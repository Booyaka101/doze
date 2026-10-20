import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from doze.compiler import compile_chore
from doze.demo import RECIPE, CASES, seed
from doze.engine import Engine, SafetyError
from doze.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.engine = Engine(root / 'workspace', root / 'state')
        seed(cls.engine)
        cls.server = make_server(cls.engine, port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.token = json.load(urllib.request.urlopen(cls.url + '/api/state'))['token']

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, body=None, token=None, origin=None, host=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Doze-Token'] = token
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers

    def test_loopback_state(self):
        code, data, _ = self.request('/api/state')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data)['token'], self.token)

    def test_csrf_required(self):
        self.assertEqual(self.request('/api/sample-recipe', {})[0], 403)

    def test_foreign_origin_rejected_even_with_token(self):
        self.assertEqual(self.request('/api/sample-recipe', {}, self.token, 'https://evil.example')[0], 403)

    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(self.request('/api/state', host='evil.example')[0], 403)

    def test_no_directory_traversal(self):
        self.assertEqual(self.request('/../engine.py')[0], 404)

    def test_static_has_csp_no_external_assets(self):
        code, data, headers = self.request('/')
        self.assertEqual(code, 200)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertNotIn(b'https://', data)

    def test_invalid_recipe_is_rejected(self):
        self.assertEqual(self.request('/api/recipe', {'recipe': {}}, self.token)[0], 400)

    def test_execute_requires_explicit_approval(self):
        self.assertEqual(self.request('/api/execute', {'plan_id': 'anything'}, self.token)[0], 400)

    def test_unknown_endpoint(self):
        self.assertEqual(self.request('/api/nope', {}, self.token)[0], 404)

    def test_sleep_gate_blocks_compiler_but_not_recipe_engine(self):
        with patch('doze.server.compiler.compile_chore', side_effect=AssertionError('Inference must not run')):
            try:
                self.assertEqual(self.request('/api/inference', {'enabled': False}, self.token)[0], 200)
                code, data, _ = self.request('/api/compile', {'prompt': 'Sort my screenshots', 'model': 'local', 'examples': CASES}, self.token)
                self.assertEqual(code, 400)
                self.assertIn('asleep', json.loads(data)['error'])
                code, data, _ = self.request('/api/sample-recipe', {}, self.token)
                self.assertEqual(code, 200)
                ident = json.loads(data)['id']
                self.assertEqual(self.request('/api/preview', {'recipe_id': ident}, self.token)[0], 200)
            finally:
                self.request('/api/inference', {'enabled': True}, self.token)

    def test_missing_examples_never_start_inference(self):
        with patch('doze.server.compiler.compile_chore', side_effect=AssertionError('No inference allowed')):
            self.assertEqual(self.request('/api/compile', {'prompt': 'Sort these screenshots', 'model': 'local'}, self.token)[0], 400)

    def test_recorded_mistake_is_blocked_even_with_explicit_api_approval(self):
        _, data, _ = self.request('/api/mistake', {}, self.token)
        saved = json.loads(data)
        self.assertFalse(saved['certificate']['certified'])
        _, data, _ = self.request('/api/preview', {'recipe_id': saved['id']}, self.token)
        plan = json.loads(data)
        code, data, _ = self.request('/api/execute', {'plan_id': plan['id'], 'approved': True}, self.token)
        self.assertEqual(code, 400)
        self.assertIn('Teaching contract blocked', json.loads(data)['error'])

    def test_exported_false_certificate_is_not_trusted(self):
        raw = json.loads(json.dumps(RECIPE))
        raw['rules'][0]['when'] = {'name_starts_with': 'screenshot'}
        code, data, _ = self.request('/api/recipe', {'recipe': raw, 'examples': CASES,
                                                  'certificate': {'certified': True}}, self.token)
        self.assertEqual(code, 200)
        self.assertFalse(json.loads(data)['certificate']['certified'])

    def test_contract_save_creates_new_version(self):
        _, data, _ = self.request('/api/sample-recipe', {}, self.token)
        saved = json.loads(data)
        code, data, _ = self.request('/api/certify', {'recipe_id': saved['id'], 'cases': CASES}, self.token)
        self.assertEqual(code, 200)
        new = json.loads(data)
        self.assertNotEqual(saved['id'], new['id'])
        self.assertEqual(saved['certificate'], new['certificate'])


class CompilerTests(unittest.TestCase):
    def test_compiler_validates_local_output(self):
        with patch('doze.compiler.models', return_value=['gemma-test']), patch('doze.compiler.request_json', return_value={
            'message': {'content': json.dumps(RECIPE)}, 'prompt_eval_count': 50, 'eval_count': 100}):
            result = compile_chore('Please organize screenshots safely', 'gemma-test')
        self.assertEqual(result['recipe'], RECIPE)
        self.assertEqual(result['provenance']['model_calls'], 1)

    def test_non_installed_model_rejected(self):
        with patch('doze.compiler.models', return_value=[]), self.assertRaisesRegex(SafetyError, 'installed'):
            compile_chore('Please organize screenshots safely', 'cloud-model')

    def test_unsafe_model_output_never_becomes_recipe(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
            'message': {'content': '{"shell":"delete everything"}'}}), self.assertRaises(SafetyError):
            compile_chore('Please organize screenshots safely', 'local')

    def test_unsupported_chore_refusal(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
            'message': {'content': '{"error":"Deletion is unsupported"}'}}), self.assertRaisesRegex(SafetyError, 'Deletion'):
            compile_chore('Please delete every file safely', 'local')

    def test_invalid_prompt(self):
        for prompt in [None, '', 'short', 'x' * 4001]:
            with self.assertRaises(SafetyError):
                compile_chore(prompt, 'local')

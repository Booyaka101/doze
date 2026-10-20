from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from doze.close import packet, profile, reconcile, validate_profile
from doze.close_cli import main
from doze.close_demo import MAPPING, PAYMENT_HEADERS, BANK_HEADERS, demo
from doze.close_inference import compile_mapping, mapping_schema
from doze.close_workflow import bench, replay_year, validate_workflow, workflow
from doze.engine import SafetyError


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.profile = profile(MAPPING, PAYMENT_HEADERS, BANK_HEADERS)

    def wrong_mapping(self):
        raw = copy.deepcopy(self.profile)
        roles = raw['mapping']['payments']
        roles['gross'], roles['fee'] = roles['fee'], roles['gross']
        return raw

    def test_all_eight_independent_witnesses_pass(self):
        proof = bench(self.profile)
        self.assertEqual((proof['passed'], proof['total']), (8, 8))
        self.assertTrue(proof['synthetic'])
        self.assertEqual(proof['model_calls'], 0)

    def test_structurally_valid_but_semantically_wrong_mapping_fails(self):
        raw = self.wrong_mapping()
        validate_profile(raw)
        proof = bench(raw)
        self.assertLess(proof['passed'], proof['total'])
        self.assertFalse(proof['checks'][0]['passed'])
        self.assertEqual(proof['checks'][0]['expected']['first_expected'], '330.28')

    def test_bench_is_reproducible_and_not_derived_from_proposed_mapping(self):
        correct = bench(self.profile)
        wrong = bench(self.wrong_mapping())
        self.assertEqual(correct['suite_sha256'], wrong['suite_sha256'])
        self.assertEqual(correct, bench(self.profile))
        self.assertNotEqual(correct['profile_sha256'], wrong['profile_sha256'])

    def test_wrong_schema_cannot_claim_a_studio_proof(self):
        raw = copy.deepcopy(self.profile)
        raw['schemas']['payments'].append('unreviewed new column')
        self.assertLess(bench(raw)['passed'], 8)
        with self.assertRaisesRegex(SafetyError, 'Workflow blocked'):
            workflow(raw)

    def test_import_recomputes_exported_proof(self):
        raw = workflow(self.profile)
        raw['proof'] = {'passed': 9999, 'sha256': 'fake'}
        checked = validate_workflow(raw)
        self.assertEqual(checked['proof']['passed'], 8)
        self.assertNotEqual(checked['proof']['sha256'], 'fake')

    def test_changed_mapping_with_old_passing_proof_is_blocked(self):
        raw = workflow(self.profile)
        raw['profile'] = self.wrong_mapping()
        data = demo('clean')
        with self.assertRaisesRegex(SafetyError, 'Workflow blocked'):
            reconcile(raw, data['payments_csv'], data['bank_csv'])

    def test_witness_version_change_requires_new_review(self):
        raw = workflow(self.profile)
        raw['suite_sha256'] = 'old-version'
        with self.assertRaisesRegex(SafetyError, 'suite changed'):
            validate_workflow(raw)

    def test_rewriting_a_bundled_expected_answer_cannot_make_it_pass(self):
        raw = workflow(self.profile)
        raw['witnesses'][0]['expect']['first_expected'] = 'fake correct answer'
        with self.assertRaisesRegex(SafetyError, 'suite changed'):
            validate_workflow(raw)

    def test_report_binds_workflow_suite_as_well_as_profile(self):
        raw = workflow(self.profile)
        data = demo('clean')
        report = reconcile(raw, data['payments_csv'], data['bank_csv'])
        self.assertEqual(report['workflow_sha256'], raw['sha256'])
        bare = reconcile(self.profile, data['payments_csv'], data['bank_csv'])
        self.assertNotEqual(report['sha256'], bare['sha256'])
        self.assertLess(len(json.dumps(raw).encode()), 64000)

    def test_nested_bundles_cannot_recurse(self):
        raw = workflow(self.profile)
        raw['profile'] = copy.deepcopy(raw)
        with self.assertRaisesRegex(SafetyError, 'non-nested'):
            validate_workflow(raw)

    def test_packet_carries_rechecked_workflow(self):
        raw = workflow(self.profile)
        data = demo('clean')
        report = reconcile(raw, data['payments_csv'], data['bank_csv'])
        content = packet(raw, data['payments_csv'], data['bank_csv'], report['sha256'])
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            saved = json.loads(archive.read('workflow.json'))
            self.assertEqual(saved, raw)
            self.assertEqual(json.loads(archive.read('profile.json')), self.profile)

    def test_year_replay_runs_offline_and_holds_all_known_bad_weeks(self):
        with patch('socket.socket', side_effect=AssertionError('No network allowed')):
            result = replay_year(workflow(self.profile))
        self.assertEqual(result['clean_weeks'], 41)
        self.assertEqual(result['held_weeks'], 11)
        self.assertEqual(result['exceptions'], 19)
        self.assertEqual(result['matched'], 193)
        self.assertEqual(result['payments'], 1248)
        self.assertEqual(result['model_calls'], 0)
        for week in result['weeks']:
            self.assertEqual(week['ready'], week['scenario'] == 'clean')

    def test_explanation_is_transmitted_as_bounded_data_not_rows(self):
        explanation = 'Payout group and Settlement reference contain the same shared payout ID.'
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
                'message': {'content': json.dumps(MAPPING)}}) as call:
            compile_mapping(PAYMENT_HEADERS, BANK_HEADERS, 'local', hint=explanation)
        body = call.call_args.args[1]
        sent = json.loads(body['messages'][1]['content'])
        self.assertEqual(sent['user_hint'], explanation)
        self.assertNotIn('SALE-01', json.dumps(sent))
        with patch('doze.compiler.generate', side_effect=AssertionError('Must reject before inference')):
            with self.assertRaises(SafetyError):
                compile_mapping(PAYMENT_HEADERS, BANK_HEADERS, 'local', hint='x' * 1001)

    def test_schema_is_grounded_in_prompt_and_restricts_each_role_to_headers(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
                'message': {'content': json.dumps(MAPPING)}}) as call:
            compile_mapping(PAYMENT_HEADERS, BANK_HEADERS, 'local')
        sent = call.call_args.args[1]
        schema = sent['format']['anyOf'][0]
        self.assertIn(json.dumps(schema), sent['messages'][0]['content'])
        for side, headers in (('payments', PAYMENT_HEADERS), ('bank', BANK_HEADERS)):
            for role in schema['properties'][side]['properties'].values():
                self.assertEqual(role['enum'], headers)
        self.assertEqual(schema['properties']['decimal_mark']['enum'], ['.'])
        self.assertEqual(sent['format']['anyOf'][1]['required'], ['error'])

    def test_dynamic_schema_does_not_mutate_global_or_other_requests(self):
        schema = mapping_schema(PAYMENT_HEADERS, BANK_HEADERS, '.')
        schema['properties']['payments']['properties']['id']['enum'] = ['changed']
        other = mapping_schema(['a', 'b', 'c', 'd', 'e'], ['w', 'x', 'y', 'z'], ',')
        self.assertEqual(other['properties']['payments']['properties']['id']['enum'], ['a', 'b', 'c', 'd', 'e'])
        self.assertEqual(other['properties']['decimal_mark']['enum'], [','])
        from doze.close import MAPPING_SCHEMA
        self.assertNotIn('enum', MAPPING_SCHEMA['properties']['payments']['properties']['id'])

    def test_grounding_keeps_refusals_supported(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
                'message': {'content': json.dumps({'error': 'Shared payout reference is unknown'})}}):
            with self.assertRaisesRegex(SafetyError, 'Shared payout reference is unknown'):
                compile_mapping(PAYMENT_HEADERS, BANK_HEADERS, 'local')

    def test_recorded_lesson_matches_actual_live_evidence(self):
        from doze.close_demo import recorded_profile
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root / 'evidence/close-grounded-teaching.json').read_text(encoding='utf-8'))
        saved = recorded_profile()
        live = evidence['cases'][0]['result']
        self.assertEqual(saved['profile'], live['profile'])
        for key, value in live['provenance'].items():
            self.assertEqual(saved['provenance'][key], value)
        self.assertTrue(saved['provenance']['recorded'])


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = demo('clean')
        self.contract = workflow(profile(MAPPING, PAYMENT_HEADERS, BANK_HEADERS))
        self.profile_path = self.root / 'workflow.json'
        self.profile_path.write_text(json.dumps(self.contract), encoding='utf-8')
        for side in ('payments', 'bank'):
            (self.root / (side + '.csv')).write_text(self.data[side + '_csv'], encoding='utf-8', newline='')
        self.args = ['--profile', str(self.profile_path), '--payments', str(self.root / 'payments.csv'),
                     '--bank', str(self.root / 'bank.csv')]

    def run_cli(self, extra):
        out, error = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(error), patch('socket.socket', side_effect=AssertionError('No network')):
            code = main(self.args + extra)
        return code, out.getvalue(), error.getvalue()

    def test_requires_explicit_mapping_review(self):
        code, out, error = self.run_cli([])
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertIn('--mapping-approved', error)

    def test_report_runs_without_server_or_network(self):
        code, out, error = self.run_cli(['--mapping-approved'])
        self.assertEqual((code, error), (0, ''))
        self.assertEqual(json.loads(out)['matched'], 4)

    def test_packet_requires_exact_previously_reviewed_hash(self):
        destination = self.root / 'handoff.zip'
        extra = ['--mapping-approved', '--packet', str(destination)]
        code, _, error = self.run_cli(extra)
        self.assertEqual(code, 2)
        self.assertIn('--approved-sha256', error)
        self.assertFalse(destination.exists())
        code, _, _ = self.run_cli(extra + ['--approved-sha256', 'wrong'])
        self.assertEqual(code, 2)
        self.assertFalse(destination.exists())
        report = reconcile(self.contract, self.data['payments_csv'], self.data['bank_csv'])
        code, _, error = self.run_cli(extra + ['--approved-sha256', report['sha256']])
        self.assertEqual((code, error), (0, ''))
        self.assertTrue(zipfile.is_zipfile(destination))

    def test_existing_output_and_input_files_are_never_overwritten(self):
        report = reconcile(self.contract, self.data['payments_csv'], self.data['bank_csv'])
        for filename in ('bank.csv', 'workflow.json', 'earlier.zip'):
            target = self.root / filename
            if not target.exists():
                target.write_bytes(b'user work')
            before = target.read_bytes()
            code, _, _ = self.run_cli(['--mapping-approved', '--packet', str(target), '--approved-sha256', report['sha256']])
            self.assertEqual(code, 2)
            self.assertEqual(target.read_bytes(), before)

    def test_exceptions_have_nonzero_exit_and_cannot_create_packet(self):
        data = demo('penny')
        (self.root / 'bank.csv').write_text(data['bank_csv'], encoding='utf-8', newline='')
        code, out, _ = self.run_cli(['--mapping-approved'])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)['ready'])
        target = self.root / 'handoff.zip'
        code, _, error = self.run_cli(['--mapping-approved', '--packet', str(target), '--approved-sha256', json.loads(out)['sha256']])
        self.assertEqual(code, 2)
        self.assertIn('unresolved exceptions', error)
        self.assertFalse(target.exists())

    def test_malformed_and_oversized_profiles_fail_cleanly(self):
        for content in ('{invalid', 'x' * 64001):
            self.profile_path.write_text(content, encoding='utf-8')
            code, out, error = self.run_cli(['--mapping-approved'])
            self.assertEqual(code, 2)
            self.assertEqual(out, '')
            self.assertTrue(error.startswith('Doze:'))

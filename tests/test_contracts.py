import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doze.compiler import compile_chore
from doze.demo import CASES, RECIPE, seed
from doze.engine import Engine, SafetyError, evaluate, validate_cases, validate_recipe
from doze.replay import replay


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.engine = Engine(root / 'workspace', root / 'state')
        seed(self.engine)

    def test_bare_recipe_cannot_execute_even_with_valid_preview(self):
        saved = self.engine.save_recipe(RECIPE)
        plan = self.engine.preview(saved['id'])
        with self.assertRaisesRegex(SafetyError, 'Teaching contract blocked'):
            self.engine.execute(plan['id'])
        self.assertEqual(self.engine.runs(), [])

    def test_recorded_mistake_is_schema_valid_but_blocked(self):
        raw = copy.deepcopy(RECIPE)
        del raw['rules'][0]['when']['extensions']
        saved = self.engine.save_recipe(raw, CASES)
        self.assertFalse(saved['certificate']['certified'])
        failed = [c['name'] for c in saved['certificate']['cases'] if not c['passed']]
        self.assertEqual(failed, ['screenshot-plan.txt'])
        with self.assertRaisesRegex(SafetyError, 'Teaching contract blocked'):
            self.engine.execute(self.engine.preview(saved['id'])['id'])

    def test_missing_destination_example_blocks_execution(self):
        cases = [c for c in CASES if c['expected'] != 'Archives']
        result = evaluate(RECIPE, cases)
        self.assertTrue(result['passed'])
        self.assertFalse(result['certified'])
        self.assertEqual(result['missing_destinations'], ['Archives'])

    def test_no_negative_example_blocks_execution(self):
        result = evaluate(RECIPE, [c for c in CASES if c['expected'] != 'HOLD'])
        self.assertTrue(result['passed'])
        self.assertFalse(result['certified'])

    def test_hold_cannot_be_a_destination(self):
        raw = copy.deepcopy(RECIPE)
        raw['rules'][0]['folder'] = 'HOLD'
        with self.assertRaisesRegex(SafetyError, 'reserved'):
            validate_recipe(raw)

    def test_contract_persists_and_is_recomputed_after_restart(self):
        saved = self.engine.save_recipe(RECIPE, CASES)
        other = Engine(self.engine.root, self.engine.database.parent)
        self.assertEqual(saved, other.package(saved['id']))

    def test_recipe_edits_do_not_inherit_certification(self):
        saved = self.engine.save_recipe(RECIPE, CASES)
        altered = copy.deepcopy(saved['recipe'])
        del altered['rules'][0]['when']['extensions']
        edited = self.engine.save_recipe(altered, saved['examples'])
        self.assertFalse(edited['certificate']['certified'])
        self.assertNotEqual(saved['certificate']['recipe_sha256'], edited['certificate']['recipe_sha256'])
        self.assertTrue(self.engine.package(saved['id'])['certificate']['certified'])

    def test_transport_recomputes_contract_instead_of_trusting_a_badge(self):
        saved = self.engine.save_recipe(RECIPE, CASES)
        exported = json.loads(json.dumps(saved))
        exported['recipe']['rules'][0]['when'] = {'name_starts_with': 'screenshot'}
        imported = self.engine.save_recipe(exported['recipe'], exported['examples'])
        self.assertFalse(imported['certificate']['certified'])

    def test_stale_contract_in_preview_is_rejected(self):
        saved = self.engine.save_recipe(RECIPE, CASES)
        plan = self.engine.preview(saved['id'])
        # Simulates external state modification. Normal API versions never mutate contracts.
        cases = CASES + [{'name': 'new-note.txt', 'expected': 'HOLD'}]
        with self.engine.db() as con:
            con.execute('UPDATE contracts SET cases=? WHERE recipe_id=?', (json.dumps(cases), saved['id']))
        with self.assertRaisesRegex(SafetyError, 'contract changed'):
            self.engine.execute(plan['id'])

    def test_receipt_carries_exact_contract_fingerprints(self):
        saved = self.engine.save_recipe(RECIPE, CASES)
        run = self.engine.execute(self.engine.preview(saved['id'])['id'])
        self.assertEqual(run['plan']['certificate'], saved['certificate'])

    def test_bad_examples_are_rejected(self):
        for cases in [[], [None], [{}], [{'name': '../x', 'expected': 'HOLD'}],
                      [{'name': 'C:x', 'expected': 'HOLD'}], [{'name': 'x', 'expected': ''}],
                      [{'name': 'x', 'expected': 'HOLD', 'bytes': True}],
                      [{'name': 'x', 'expected': 'HOLD', 'bytes': -1}],
                      [{'name': 'x', 'expected': 'HOLD', 'extra': 'ignored?'}],
                      [{'name': 'X', 'expected': 'HOLD'}, {'name': 'x', 'expected': 'Finance'}]]:
            with self.subTest(cases=cases), self.assertRaises(SafetyError):
                validate_cases(cases)

    def test_size_examples_test_actual_threshold(self):
        recipe = {'name': 'Large zips', 'description': 'Keep small ZIP files.', 'rules': [
            {'label': 'Large ZIP', 'folder': 'Large', 'when': {'extensions': ['.zip'], 'min_bytes': 2048}}]}
        cases = [{'name': 'file.zip', 'bytes': 2047, 'expected': 'HOLD'},
                 {'name': 'file.zip', 'bytes': 2048, 'expected': 'Large'}]
        self.assertTrue(evaluate(recipe, cases)['certified'])

    def test_repair_receives_only_explicit_examples_and_previous_recipe(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
                'message': {'content': json.dumps(RECIPE)}}) as request:
            result = compile_chore('Repair the screenshot rule please', 'local', CASES, RECIPE)
        user = json.loads(request.call_args.args[1]['messages'][1]['content'])
        self.assertEqual(user['user_labelled_examples'], CASES)
        self.assertEqual(user['previous_recipe'], RECIPE)
        self.assertTrue(user['deterministic_feedback']['certified'])
        self.assertEqual(result['provenance']['model_calls'], 1)

    def test_replay_runs_moves_without_network_and_does_not_touch_workspace(self):
        before = sorted(p.name for p in self.engine.root.iterdir())
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('No network permitted')):
            result = replay(RECIPE, self.temp.name, days=3)
        self.assertTrue(result['passed'])
        self.assertEqual(result['moves'], 15)
        self.assertEqual(result['files'], 36)
        self.assertTrue(result['last_batch_undo_verified'])
        self.assertTrue(result['all_hashes_verified'])
        self.assertEqual(before, sorted(p.name for p in self.engine.root.iterdir()))

    def test_replay_rejects_wrong_scenario_without_moves(self):
        bad = copy.deepcopy(RECIPE)
        del bad['rules'][0]['when']['extensions']
        result = replay(bad, self.temp.name, days=2)
        self.assertFalse(result['passed'])
        self.assertEqual(len(result['mismatches']), 2)

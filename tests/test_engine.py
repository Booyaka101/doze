import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doze.demo import RECIPE, seed
from doze.engine import Engine, SafetyError, digest, matches, validate_recipe


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.engine = Engine(root / 'workspace', root / 'state')
        seed(self.engine)
        self.saved = self.engine.save_recipe(RECIPE)

    def preview(self):
        return self.engine.preview(self.saved['id'])

    def snapshot(self):
        return {p.relative_to(self.engine.root).as_posix(): digest(p)
                for p in self.engine.root.rglob('*') if p.is_file()}

    def test_demo_plan_moves_five_holds_four_without_mutation(self):
        before = self.snapshot()
        plan = self.preview()
        self.assertEqual(len(plan['moves']), 5)
        self.assertEqual(len(plan['held']), 4)
        self.assertEqual(plan['model_calls'], 0)
        self.assertEqual(before, self.snapshot())

    def test_run_and_undo_restore_all_bytes(self):
        before = self.snapshot()
        run = self.engine.execute(self.preview()['id'])
        self.assertEqual(run['status'], 'completed')
        self.assertTrue(all(a['status'] == 'moved' for a in run['actions']))
        self.assertEqual(len(self.engine.inventory()), 7)
        self.assertEqual(self.engine.undo(run['id'])['status'], 'undone')
        self.assertEqual(self.snapshot(), before)

    def test_edited_source_blocks_entire_run(self):
        plan = self.preview()
        self.engine.path(plan['moves'][-1]['source']).write_bytes(b'CHANGED')
        before = self.snapshot()
        with self.assertRaisesRegex(SafetyError, 'changed since preview'):
            self.engine.execute(plan['id'])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.engine.runs(), [])

    def test_destination_appearing_after_preview_blocks_every_move(self):
        plan = self.preview()
        target = self.engine.path(plan['moves'][-1]['destination'])
        target.parent.mkdir(parents=True)
        target.write_bytes(b'KEEP ME')
        before = self.snapshot()
        with self.assertRaisesRegex(SafetyError, 'Destination exists'):
            self.engine.execute(plan['id'])
        self.assertEqual(before, self.snapshot())

    def test_existing_destination_is_held(self):
        plan = self.preview()
        target = self.engine.path(plan['moves'][0]['destination'])
        target.parent.mkdir(parents=True)
        target.write_bytes(b'KEEP')
        second = self.preview()
        self.assertEqual(len(second['moves']), 4)
        self.assertTrue(any('already exists' in item['reason'] for item in second['held']))

    def test_plan_is_single_use_even_after_undo(self):
        plan = self.preview()
        run = self.engine.execute(plan['id'])
        self.engine.undo(run['id'])
        with self.assertRaisesRegex(SafetyError, 'already used'):
            self.engine.execute(plan['id'])

    def test_double_undo_is_rejected(self):
        run = self.engine.execute(self.preview()['id'])
        self.engine.undo(run['id'])
        with self.assertRaisesRegex(SafetyError, 'already undone'):
            self.engine.undo(run['id'])

    def test_edited_destination_blocks_entire_undo(self):
        run = self.engine.execute(self.preview()['id'])
        self.engine.path(run['actions'][-1]['destination']).write_bytes(b'IMPORTANT EDIT')
        before = self.snapshot()
        with self.assertRaisesRegex(SafetyError, 'changed after'):
            self.engine.undo(run['id'])
        self.assertEqual(before, self.snapshot())

    def test_new_source_blocks_undo_without_overwriting(self):
        run = self.engine.execute(self.preview()['id'])
        self.engine.path(run['actions'][0]['source']).write_bytes(b'NEW FILE')
        before = self.snapshot()
        with self.assertRaisesRegex(SafetyError, 'already exists'):
            self.engine.undo(run['id'])
        self.assertEqual(before, self.snapshot())

    def test_second_batch_does_not_need_a_model(self):
        self.engine.execute(self.preview()['id'])
        seed(self.engine, 'next')
        with patch('doze.compiler.request_json', side_effect=AssertionError('No inference allowed')):
            plan = self.preview()
            self.assertEqual(len(plan['moves']), 5)
            run = self.engine.execute(plan['id'])
            self.engine.undo(run['id'])

    def test_first_match_wins(self):
        recipe = copy.deepcopy(RECIPE)
        recipe['rules'].insert(0, {'label': 'First', 'when': {'extensions': ['.pdf']}, 'folder': 'First'})
        saved = self.engine.save_recipe(recipe)
        plan = self.engine.preview(saved['id'])
        self.assertTrue(all(m['destination'].startswith('First/') for m in plan['moves'] if m['source'].endswith('.pdf')))

    def test_protected_files_cannot_be_opted_back_in(self):
        saved = self.engine.save_recipe({'name': 'All', 'description': 'Size rule', 'rules': [
            {'label': 'All', 'when': {'min_bytes': 0}, 'folder': 'All'}]})
        plan = self.engine.preview(saved['id'])
        self.assertEqual(len(plan['moves']), 7)
        self.assertTrue(all(not m['source'].startswith('.') and not m['source'].endswith('.ps1') for m in plan['moves']))

    def test_no_recursive_scan(self):
        folder = self.engine.root / 'Nested'
        folder.mkdir()
        (folder / 'invoice.pdf').write_bytes(b'keep')
        self.assertEqual(len(self.preview()['moves']), 5)

    def test_paths_cannot_escape(self):
        for path in ['../out', '/out', 'C:/out', 'a\\b', 'a/../b', 'a//b', './x', '']:
            with self.subTest(path=path), self.assertRaises(SafetyError):
                self.engine.path(path)

    def test_linked_destination_is_rejected(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        try:
            (self.engine.root / 'Finance').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation not permitted by this operating system account.')
        plan = self.preview()
        self.assertEqual(len(plan['moves']), 3)
        self.assertEqual(list(outside.iterdir()), [])

    def test_interrupted_move_has_recoverable_receipt(self):
        before = self.snapshot()
        original = Path.unlink
        broken = False

        def fail_once(path, *args, **kwargs):
            nonlocal broken
            if path.parent == self.engine.root and not broken:
                broken = True
                raise OSError('Simulated power-loss boundary')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'unlink', fail_once), self.assertRaisesRegex(SafetyError, 'interrupted'):
            self.engine.execute(self.preview()['id'])
        run = self.engine.runs()[0]
        self.assertEqual(run['status'], 'interrupted')
        self.assertEqual(run['actions'][0]['status'], 'linked')
        self.engine.undo(run['id'])
        self.assertEqual(self.snapshot(), before)

    def test_link_failure_never_removes_source(self):
        before = self.snapshot()
        with patch('doze.engine.os.link', side_effect=OSError('Unsupported filesystem')):
            with self.assertRaises(SafetyError):
                self.engine.execute(self.preview()['id'])
        self.assertEqual(before, self.snapshot())
        self.engine.undo(self.engine.runs()[0]['id'])

    def test_recipe_round_trip_and_persistence(self):
        engine = Engine(self.engine.root, self.engine.database.parent)
        self.assertEqual(engine.recipe(self.saved['id']), RECIPE)
        self.assertEqual(json.loads(json.dumps(RECIPE)), RECIPE)

    def test_state_cannot_be_reused_for_a_different_workspace(self):
        with self.assertRaisesRegex(SafetyError, 'different workspace'):
            Engine(Path(self.temp.name) / 'different', self.engine.database.parent)

    def test_source_missing_rejects_preview(self):
        plan = self.preview()
        self.engine.path(plan['moves'][0]['source']).unlink()
        with self.assertRaisesRegex(SafetyError, 'changed since preview'):
            self.engine.execute(plan['id'])

    def test_no_match_is_not_an_execution(self):
        saved = self.engine.save_recipe({'name': 'Nothing', 'description': 'No match', 'rules': [
            {'label': 'No match', 'when': {'extensions': ['.abc']}, 'folder': 'Nothing'}]})
        with self.assertRaisesRegex(SafetyError, 'no approved moves'):
            self.engine.execute(self.engine.preview(saved['id'])['id'])

    def test_demo_never_overwrites(self):
        file = self.engine.root / '.env.example'
        file.write_bytes(b'USER EDIT')
        seed(self.engine)
        self.assertEqual(file.read_bytes(), b'USER EDIT')

    def test_near_miss_lab_catches_overbroad_model_rule(self):
        recipe = copy.deepcopy(RECIPE)
        del recipe['rules'][0]['when']['extensions']
        saved = self.engine.save_recipe(recipe)
        result = self.engine.probe(saved['id'], [{'name': 'screenshot-plan.txt', 'expected': 'HOLD'}])
        self.assertFalse(result['passed'])
        self.assertEqual(result['cases'][0]['actual'], 'Screenshots')

    def test_near_miss_lab_accepts_precise_rules(self):
        cases = [{'name': 'screenshot-plan.txt', 'expected': 'HOLD'},
                 {'name': 'screenshot-design.png', 'expected': 'Screenshots'},
                 {'name': 'invoice.pdf', 'expected': 'Finance'},
                 {'name': '.env', 'expected': 'HOLD'}]
        before = self.snapshot()
        self.assertTrue(self.engine.probe(self.saved['id'], cases)['passed'])
        self.assertEqual(before, self.snapshot())


class RecipeTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_recipe(RECIPE), RECIPE)

    def test_malformed_recipes(self):
        invalid = [None, [], {}, {**RECIPE, 'shell': 'rm -rf'}, {**RECIPE, 'rules': []},
                   {**RECIPE, 'name': ''}, {**RECIPE, 'rules': [None]}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(SafetyError):
                validate_recipe(value)

    def test_unsafe_folders(self):
        for folder in ['../escape', '/absolute', 'C:/drive', 'a\\b', 'a//b', 'a/CON', 'a/../b', 'a;rm', '{year}', 'x ', '.hidden', 'a/b/c/d/e']:
            recipe = copy.deepcopy(RECIPE)
            recipe['rules'][0]['folder'] = folder
            with self.subTest(folder=folder), self.assertRaises(SafetyError):
                validate_recipe(recipe)

    def test_invalid_conditions(self):
        for when in [{}, {'shell': 'echo'}, {'extensions': []}, {'extensions': ['png']},
                     {'name_contains': ['']}, {'name_starts_with': ''}, {'min_bytes': -1},
                     {'min_bytes': True}, {'max_bytes': '12'}, {'min_bytes': 5, 'max_bytes': 2}]:
            recipe = copy.deepcopy(RECIPE)
            recipe['rules'][0]['when'] = when
            with self.subTest(when=when), self.assertRaises(SafetyError):
                validate_recipe(recipe)

    def test_and_or_semantics_and_case_insensitivity(self):
        when = {'extensions': ['.PDF'], 'name_contains': ['receipt', 'invoice'], 'min_bytes': 4, 'max_bytes': 10}
        self.assertTrue(matches(when, 'INVOICE.PDF', 5))
        self.assertTrue(matches(when, 'receipt.pdf', 10))
        self.assertFalse(matches(when, 'invoice.txt', 5))
        self.assertFalse(matches(when, 'other.pdf', 5))
        self.assertFalse(matches(when, 'invoice.pdf', 11))
        self.assertFalse(matches(when, 'invoice.pdf', 3))


if __name__ == '__main__':
    unittest.main()

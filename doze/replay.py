"""A labelled, synthetic 30-day replay. Not evidence of real user time saved."""
from pathlib import Path
import tempfile
import time

from .demo import CASES
from .engine import Engine, classify, digest, validate_recipe


def fixtures(day):
    suffix = f'day-{day:02d}'
    # These labels are the Friday-reset specification, not model-generated answers.
    return [
        (f'Screenshot-{suffix}.png', 'Screenshots'),
        (f'screenshot-design-{suffix}.webp', 'Screenshots'),
        (f'invoice-studio-{suffix}.pdf', 'Finance'),
        (f'coffee-receipt-{suffix}.pdf', 'Finance'),
        (f'assets-{suffix}.zip', 'Archives'),
        (f'screenshot-plan-{suffix}.txt', 'HOLD'),
        (f'holiday-{suffix}.jpg', 'HOLD'),
        (f'invoice-notes-{suffix}.txt', 'HOLD'),
        (f'readme-{suffix}.pdf', 'HOLD'),
        (f'.env-{suffix}', 'HOLD'),
        (f'cleanup-{suffix}.ps1', 'HOLD'),
        (f'notes-{suffix}.txt', 'HOLD')]


def replay(recipe, parent=None, days=30):
    recipe = validate_recipe(recipe)
    started = time.perf_counter()
    mismatches = []
    for day in range(1, days + 1):
        for name, expected in fixtures(day):
            actual = classify(recipe, name, len(b'DOZE SYNTHETIC REPLAY\n'))
            if actual != expected:
                mismatches.append({'name': name, 'expected': expected, 'actual': actual})
    if mismatches:
        return {'passed': False, 'mismatches': mismatches[:20], 'model_calls': 0,
                'scope': 'This recipe does not match the fixed Friday-reset scenario. No moves were attempted.'}
    with tempfile.TemporaryDirectory(prefix='replay-', dir=parent) as temporary:
        root = Path(temporary)
        engine = Engine(root / 'workspace', root / 'state')
        saved = engine.save_recipe(recipe, CASES)
        results = []
        for day in range(1, days + 1):
            batch = fixtures(day)
            for name, _ in batch:
                (engine.root / name).write_bytes(b'DOZE SYNTHETIC REPLAY\n')
            plan = engine.preview(saved['id'])
            run = engine.execute(plan['id'])
            results.append({'day': day, 'new_files': len(batch), 'moved': len(plan['moves']), 'model_calls': 0})
        # Every fixture must still have exactly the expected bytes at its intended path.
        expected_hash = digest(engine.path(fixtures(days)[-1][0]))
        for day in range(1, days + 1):
            for name, folder in fixtures(day):
                relative = name if folder == 'HOLD' else folder + '/' + name
                if digest(engine.path(relative)) != expected_hash:
                    raise AssertionError('Replay changed fixture bytes.')
        last = engine.undo(run['id'])
        undo_verified = last['status'] == 'undone' and all(
            (engine.root / name).is_file() and digest(engine.root / name) == expected_hash
            and (folder == 'HOLD' or not (engine.root / folder / name).exists())
            for name, folder in fixtures(days))
    return {'passed': True, 'days': days, 'files': days * 12, 'moves': days * 5,
            'held': days * 7, 'model_calls': 0, 'all_hashes_verified': True,
            'last_batch_undo_verified': undo_verified, 'batches': results,
            'elapsed_seconds': round(time.perf_counter() - started, 3),
            'scope': 'Synthetic Friday-reset workload, not real usage or measured human time saved. Isolated temporary workspace. No inference.'}

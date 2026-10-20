"""Run two synthetic batches with all urllib network access forbidden."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doze.demo import RECIPE, seed
from doze.engine import Engine, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiled', type=Path, help='Compiler response or recipe JSON; otherwise use the hand-written sample.')
    args = parser.parse_args()
    raw = json.loads(args.compiled.read_text()) if args.compiled else {'recipe': RECIPE}
    recipe = raw.get('recipe', raw)
    project = Path(__file__).resolve().parents[1]
    (project / '.doze').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='proof-', dir=project / '.doze') as temporary:
        root = Path(temporary)
        engine = Engine(root / 'workspace', root / 'state')
        seed(engine)
        saved = engine.save_recipe(recipe)
        results = []
        receipts = []
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Network forbidden during repeat runs')):
            for batch in ['first', 'next']:
                if batch == 'next':
                    seed(engine, batch)
                before = {p.relative_to(engine.root).as_posix(): digest(p) for p in engine.root.rglob('*') if p.is_file()}
                started = time.perf_counter()
                plan = engine.preview(saved['id'])
                run = engine.execute(plan['id'])
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                assert len(plan['moves']) == 5, 'Friday-reset fixture should have exactly five moves.'
                receipts.append((run, before))
                results.append({'batch': batch, 'moves': len(plan['moves']), 'model_calls': 0,
                                'preview_and_run_ms': elapsed})
            for index in reversed(range(len(receipts))):
                run, before = receipts[index]
                engine.undo(run['id'])
                after = {p.relative_to(engine.root).as_posix(): digest(p) for p in engine.root.rglob('*') if p.is_file()}
                assert all(after.get(path) == sha for path, sha in before.items()), 'Undo must restore every prior path and byte.'
                results[index]['undo_restored_all_hashes'] = True
    report = {'recipe_source': 'saved compiler result' if args.compiled else 'hand-written sample',
              'network_forbidden': True, 'results': results,
              'scope': 'Synthetic files only; timings are local observations, not human time-saved claims.'}
    (project / 'evidence').mkdir(exist_ok=True)
    (project / 'evidence' / 'model-free-proof.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

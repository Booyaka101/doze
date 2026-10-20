"""Cold CLI subprocess proof with all socket creation blocked. Synthetic data only."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doze.close_demo import demo

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''import runpy, socket, sys
def forbidden(*args, **kwargs):
    raise AssertionError("Network forbidden in offline CLI proof")
socket.socket = forbidden
socket.create_connection = forbidden
sys.argv = ["doze.close_cli"] + sys.argv[1:]
runpy.run_module("doze.close_cli", run_name="__main__")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recorded-gemma', action='store_true', help='Prove the saved live-model workflow instead of the manual sample')
    args = parser.parse_args()
    suffix = '-gemma' if args.recorded_gemma else ''
    workflow = json.loads((ROOT / f'evidence/close-tested-workflow{suffix}.json').read_text(encoding='utf-8'))
    checks = []
    (ROOT / '.doze').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cli-proof-', dir=ROOT / '.doze') as temp:
        root = Path(temp)
        profile = root / 'workflow.json'
        profile.write_text(json.dumps(workflow), encoding='utf-8')
        payments, bank = root / 'payments.csv', root / 'bank.csv'
        arguments = ['--profile', str(profile), '--payments', str(payments), '--bank', str(bank), '--mapping-approved']

        def invoke(extra=()):
            return subprocess.run([sys.executable, '-c', BOOTSTRAP, *arguments, *extra],
                                  cwd=ROOT, text=True, capture_output=True, timeout=15)

        def require(condition, name):
            if not condition:
                raise AssertionError(name)
            checks.append(name)

        clean_report = None
        for scenario in ('clean', 'penny', 'messy'):
            data = demo(scenario)
            payments.write_text(data['payments_csv'], encoding='utf-8', newline='')
            bank.write_text(data['bank_csv'], encoding='utf-8', newline='')
            response = invoke()
            require(response.returncode == (0 if scenario == 'clean' else 2), scenario + ' exit status')
            report = json.loads(response.stdout)
            require(report['ready'] == (scenario == 'clean'), scenario + ' verdict')
            if scenario == 'clean':
                clean_report = report
        data = demo('clean')
        payments.write_text(data['payments_csv'], encoding='utf-8', newline='')
        bank.write_text(data['bank_csv'], encoding='utf-8', newline='')
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (profile, payments, bank)}
        destination = root / 'handoff.zip'
        packet_args = ['--packet', str(destination), '--approved-sha256', clean_report['sha256']]
        response = invoke(packet_args)
        require(response.returncode == 0 and zipfile.is_zipfile(destination), 'reviewed offline ZIP created')
        with zipfile.ZipFile(destination) as archive:
            require('workflow.json' in archive.namelist(), 'packet carries executable synthetic witnesses')
            require(json.loads(archive.read('audit.json'))['sha256'] == clean_report['sha256'], 'packet audit matches approved report')
        before = destination.read_bytes()
        require(invoke(packet_args).returncode == 2 and destination.read_bytes() == before, 'existing packet preserved')
        data = demo('clean', 2)
        bank.write_text(data['bank_csv'], encoding='utf-8', newline='')
        changed = invoke(['--packet', str(root / 'stale.zip'), '--approved-sha256', clean_report['sha256']])
        require(changed.returncode == 2 and not (root / 'stale.zip').exists(), 'changed input rejects old approval')
        require(hashlib.sha256(profile.read_bytes()).hexdigest() == hashes[profile.name]
                and hashlib.sha256(payments.read_bytes()).hexdigest() == hashes[payments.name], 'mapping and payment input bytes unchanged')
        evidence = {'synthetic': True, 'mapping_source': 'recorded Gemma output from close-grounded-teaching.json' if args.recorded_gemma else 'hand-written sample, not AI output',
                    'execution': 'fresh Python CLI subprocesses with socket creation blocked', 'network_calls': 0,
                    'model_calls': 0, 'checks': checks, 'workflow_sha256': workflow['sha256'],
                    'approved_report_sha256': clean_report['sha256'], 'packet_bytes': len(before)}
    (ROOT / f'evidence/close-offline-proof{suffix}.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()

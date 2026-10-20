"""Versioned synthetic witnesses for the studio schema, not accounting certification."""
from collections import Counter
import time

from .close import reconcile, table, validate_profile
from .close_demo import csv_text, demo
from .engine import SafetyError, fingerprint

SUITE = 'studio-witnesses-v1'
FORMAT = 'doze-close-workflow-v1'


def change(data, side, record, column, value):
    data = dict(data)
    headers, rows = table(data[side + '_csv'])
    rows[record - 1]['values'][column] = value
    data[side + '_csv'] = csv_text(headers, [[r['values'][h] for h in headers] for r in rows])
    return data


def witnesses():
    clean = demo('clean')
    refund = change(clean, 'payments', 1, 'Customer paid', '-52.00')
    refund = change(refund, 'bank', 1, 'Money received', '226.28')
    missing = dict(clean)
    headers, rows = table(clean['bank_csv'])
    missing['bank_csv'] = csv_text(headers, [[r['values'][h] for h in headers] for r in rows[1:]])
    return [
        {'name': 'Clean close', 'data': clean, 'expect': {'ready': True, 'matched': 4, 'statuses': {'matched': 4},
            'first_expected': '330.28', 'gross_usd': '1620.00'}},
        {'name': 'One cent is not close enough', 'data': demo('penny'), 'expect': {
            'ready': False, 'matched': 3, 'statuses': {'matched': 3, 'mismatch': 1}, 'difference': '-0.01'}},
        {'name': 'Duplicate and orphan transfers', 'data': demo('messy'), 'expect': {
            'ready': False, 'matched': 2, 'statuses': {'matched': 2, 'mismatch': 1, 'ambiguous': 1, 'orphan': 1}}},
        {'name': 'Schema change stops the close', 'data': demo('drift'), 'expect': {'error': 'Schema drift'}},
        {'name': 'Duplicate sale IDs quarantine both batches',
            'data': change(clean, 'payments', 7, 'Sale reference', 'SALE-01-1-1'),
            'expect': {'ready': False, 'matched': 2, 'issues': 2, 'statuses': {'matched': 2, 'invalid': 2}}},
        {'name': 'Currencies are not interchangeable', 'data': change(clean, 'payments', 1, 'ISO currency', 'EUR'),
            'expect': {'ready': False, 'matched': 3, 'statuses': {'matched': 3, 'currency_conflict': 1}}},
        {'name': 'Missing transfer is not guessed', 'data': missing, 'expect': {
            'ready': False, 'matched': 3, 'statuses': {'matched': 3, 'missing': 1}}},
        {'name': 'Refund stays an exact negative amount', 'data': refund, 'expect': {
            'ready': True, 'matched': 4, 'statuses': {'matched': 4}, 'first_expected': '226.28', 'gross_usd': '1516.00'}}]


def bench(raw_profile):
    contract = validate_profile(raw_profile)
    cases = witnesses()
    results = []
    for case in cases:
        expected = case['expect']
        try:
            report = reconcile(contract, case['data']['payments_csv'], case['data']['bank_csv'])
            observed = {'ready': report['ready'], 'matched': report['matched'], 'issues': len(report['issues']),
                        'statuses': dict(Counter(s['status'] for s in report['settlements'])),
                        'first_expected': report['settlements'][0]['expected'] if report['settlements'] else None,
                        'gross_usd': report['totals'].get('USD', {}).get('gross')}
            if 'difference' in expected:
                observed['difference'] = next((s['difference'] for s in report['settlements'] if s['status'] == 'mismatch'), None)
            passed = all(observed.get(key) == value for key, value in expected.items())
        except SafetyError as error:
            observed = {'error': str(error)}
            passed = 'error' in expected and str(error).startswith(expected['error'])
        results.append({'name': case['name'], 'passed': passed, 'expected': expected, 'observed': observed})
    proof = {'suite': SUITE, 'suite_sha256': fingerprint(cases), 'profile_sha256': contract['sha256'],
             'passed': sum(r['passed'] for r in results), 'total': len(results), 'checks': results,
             'model_calls': 0, 'synthetic': True,
             'scope': 'Known studio schema only. Fixture agreement is not proof of source completeness or real-world suitability.'}
    proof['sha256'] = fingerprint(proof)
    return proof


def workflow(raw_profile):
    contract = validate_profile(raw_profile)
    proof = bench(contract)
    if proof['passed'] != proof['total']:
        raise SafetyError(f"Workflow blocked: mapping passed {proof['passed']}/{proof['total']} synthetic witnesses.")
    return {'format': FORMAT, 'profile': contract, 'suite': SUITE,
            'suite_sha256': proof['suite_sha256'], 'witnesses': witnesses(), 'proof': proof,
            'sha256': fingerprint({'profile_sha256': contract['sha256'], 'suite_sha256': proof['suite_sha256']})}


def validate_workflow(raw):
    if (not isinstance(raw, dict) or raw.get('format') != FORMAT or raw.get('suite') != SUITE
            or not isinstance(raw.get('profile'), dict) or raw['profile'].get('format') != 'doze-close-v1'):
        raise SafetyError('Choose a supported Doze workflow with a non-nested mapping.')
    # Exported pass flags are never authoritative. Rerun the installed witness suite.
    checked = workflow(raw['profile'])
    if (raw.get('suite_sha256') != checked['suite_sha256']
            or fingerprint(raw.get('witnesses')) != checked['suite_sha256']):
        raise SafetyError('The workflow witness suite changed. Review and test a new workflow explicitly.')
    return checked


def replay_year(raw_profile):
    contract = validate_profile(raw_profile)
    started = time.perf_counter()
    weeks = []
    for week in range(1, 53):
        scenario = 'messy' if week % 13 == 0 else 'penny' if week % 7 == 0 else 'clean'
        data = demo(scenario, week)
        report = reconcile(contract, data['payments_csv'], data['bank_csv'])
        weeks.append({'week': week, 'scenario': scenario, 'ready': report['ready'], 'matched': report['matched'],
                      'exceptions': report['exceptions'], 'report_sha256': report['sha256']})
    return {'synthetic': True, 'weeks': weeks, 'clean_weeks': sum(w['ready'] for w in weeks),
            'held_weeks': sum(not w['ready'] for w in weeks), 'payments': 1248,
            'matched': sum(w['matched'] for w in weeks), 'exceptions': sum(w['exceptions'] for w in weeks),
            'model_calls': 0, 'seconds': round(time.perf_counter() - started, 4),
            'profile_sha256': contract['sha256'],
            'scope': '52 generated weeks, not customer history, a scheduler, or measured human time saved.'}

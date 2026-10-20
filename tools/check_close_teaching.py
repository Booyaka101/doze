"""At most three different synthetic teaching cases. No retries or row values."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doze.close import profile
from doze.close_demo import MAPPING, PAYMENT_HEADERS, BANK_HEADERS
from doze.close_inference import compile_mapping
from doze.close_workflow import bench
from doze.engine import SafetyError

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'evidence/close-grounded-teaching.json'


def main():
    if DESTINATION.exists():
        raise SystemExit('Evidence already exists. Refusing an automatic repeat of the model calls.')
    old = json.loads((ROOT / 'evidence/close-explained-teaching.json').read_text(encoding='utf-8'))['sent']
    alternate_payments = ['charge_id', 'payout_ref', 'gross_amount', 'fee_amount', 'currency']
    alternate_bank = ['entry_id', 'payout_ref', 'net_amount', 'currency']
    alternate = {'name': 'Alternate mapping', 'decimal_mark': '.',
                 'payments': dict(zip(MAPPING['payments'], alternate_payments)),
                 'bank': dict(zip(MAPPING['bank'], alternate_bank))}
    cases = [
        {'name': 'Explained studio schema', 'payments': PAYMENT_HEADERS, 'bank': BANK_HEADERS,
         'hint': old['hint'], 'expected': MAPPING},
        {'name': 'Different explicit vocabulary', 'payments': alternate_payments, 'bank': alternate_bank,
         'hint': 'Both payout_ref columns contain the same shared payout ID. charge_id identifies each sale. entry_id identifies a bank row, not a payout. gross_amount is customer gross before fee_amount; net_amount is what the bank received. currency is the ISO code.',
         'expected': alternate},
        {'name': 'Unknown meanings must not be guessed', 'payments': ['A', 'B', 'C', 'D', 'E'],
         'bank': ['W', 'X', 'Y', 'Z'],
         'hint': 'These are arbitrary column labels. Their meanings are unknown. There is no known shared payout reference and no role mapping. Ask for an explanation instead of choosing arbitrary columns.',
         'expected': None}]
    evidence = {'synthetic': True, 'model': old['model'], 'maximum_model_calls': 3,
                'change': 'Mapping schema grounded in system prompt; role values restricted to actual column enums. Refusal branch retained.',
                'official_reference': 'https://docs.ollama.com/capabilities/structured-outputs', 'cases': []}
    for case in cases:
        record = {key: value for key, value in case.items() if key != 'expected'}
        try:
            result = compile_mapping(case['payments'], case['bank'], old['model'], hint=case['hint'])
            record['result'] = result
            if case['expected'] is None:
                record['passed'] = False
                record['failure'] = 'The model proposed a mapping despite explicitly unknown meanings.'
            else:
                expected = profile(case['expected'], case['payments'], case['bank'])['mapping']
                observed = result['profile']['mapping']
                record['passed'] = all(observed[key] == expected[key] for key in ('decimal_mark', 'payments', 'bank'))
                if case['payments'] == PAYMENT_HEADERS:
                    record['witnesses'] = bench(result['profile'])
                    record['passed'] = record['passed'] and record['witnesses']['passed'] == 8
        except SafetyError as error:
            record['error'] = str(error)
            record['passed'] = case['expected'] is None and 'could not express' in str(error)
        evidence['cases'].append(record)
        # Save every observed outcome immediately. Interrupted runs must not silently restart.
        DESTINATION.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'case': case['name'], 'passed': record['passed'], 'error': record.get('error')}), flush=True)
    evidence['passed'] = all(case['passed'] for case in evidence['cases'])
    evidence['observed_model_calls'] = len(evidence['cases'])
    DESTINATION.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

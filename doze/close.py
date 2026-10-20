"""Exact payout reconciliation. Models may map column names, never calculate money."""
import csv
import hashlib
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import io
import json
import re
import zipfile

from .engine import SafetyError, fingerprint

ROLES = {'payments': ('id', 'batch', 'gross', 'fee', 'currency'),
         'bank': ('id', 'batch', 'amount', 'currency')}
CURRENCIES = {'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'NZD', 'CHF'}
MAPPING_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['name', 'decimal_mark', 'payments', 'bank'],
    'properties': {
        'name': {'type': 'string'}, 'decimal_mark': {'type': 'string', 'enum': ['.', ',']},
        **{side: {'type': 'object', 'additionalProperties': False, 'required': list(roles),
                  'properties': {role: {'type': 'string'} for role in roles}}
           for side, roles in ROLES.items()}}}


def table(text):
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 350000:
        raise SafetyError('Each CSV must be nonempty UTF-8 text, at most 350 KB.')
    try:
        reader = csv.reader(io.StringIO(text.lstrip('\ufeff'), newline=''), strict=True)
        headers = next(reader)
        if (not 1 <= len(headers) <= 40 or len(set(headers)) != len(headers)
                or any(not h.strip() or len(h) > 120 for h in headers)):
            raise SafetyError('CSV headers must be unique, nonempty names (maximum 40).')
        rows = []
        for index, values in enumerate(reader, start=1):
            if len(values) != len(headers):
                raise SafetyError(f'CSV data record {index} has the wrong number of columns. Nothing was reconciled.')
            if any(len(v) > 1000 or '\x00' in v for v in values):
                raise SafetyError('CSV cells must be at most 1,000 characters, without NUL bytes.')
            rows.append({'record': index, 'values': dict(zip(headers, values))})
            if len(rows) > 2000:
                raise SafetyError('Limit is 2,000 data records per CSV.')
    except (csv.Error, StopIteration) as error:
        raise SafetyError('Invalid CSV. Use comma-separated UTF-8 with a header row.') from error
    if not rows:
        raise SafetyError('CSV has no data records.')
    return headers, rows


def profile(mapping, payment_headers, bank_headers):
    if not isinstance(mapping, dict) or set(mapping) != {'name', 'decimal_mark', 'payments', 'bank'}:
        raise SafetyError('Mapping needs only name, decimal_mark, payments and bank.')
    if not isinstance(mapping['name'], str) or not 1 <= len(mapping['name']) <= 120:
        raise SafetyError('Give the mapping a short name.')
    if mapping['decimal_mark'] not in ('.', ','):
        raise SafetyError('Choose a decimal point or comma explicitly.')
    schemas = {'payments': payment_headers, 'bank': bank_headers}
    for side, roles in ROLES.items():
        headers = schemas[side]
        if (not isinstance(headers, list) or not headers or len(headers) > 40
                or any(not isinstance(h, str) or not h.strip() or len(h) > 120 for h in headers)
                or len(headers) != len(set(headers))):
            raise SafetyError('Invalid schema headers.')
        columns = mapping[side]
        if not isinstance(columns, dict) or set(columns) != set(roles):
            raise SafetyError(f'Every {side} role must be mapped exactly once.')
        if (any(not isinstance(v, str) or v not in headers for v in columns.values())
                or len(set(columns.values())) != len(columns)):
            raise SafetyError('Mapped columns must exist and cannot serve two roles.')
    return {'format': 'doze-close-v1', 'mapping': json.loads(json.dumps(mapping)),
            'schemas': schemas, 'sha256': fingerprint({'mapping': mapping, 'schemas': schemas})}


def validate_profile(raw):
    if not isinstance(raw, dict) or raw.get('format') != 'doze-close-v1' or not isinstance(raw.get('schemas'), dict):
        raise SafetyError('Choose a Doze close profile, not a file-sorting recipe.')
    return profile(raw.get('mapping'), raw['schemas'].get('payments'), raw['schemas'].get('bank'))


def money(raw, mark):
    # No float conversion, implicit rounding, currency symbols or guessed separators.
    if not re.fullmatch(r'-?\d{1,12}(?:' + re.escape(mark) + r'\d{1,2})?', raw):
        raise SafetyError('Amount is not an exact plain decimal with at most two fractional digits.')
    try:
        return Decimal(raw.replace(mark, '.')).quantize(Decimal('.01'))
    except InvalidOperation as error:
        raise SafetyError('Invalid monetary amount.') from error


def reconcile(raw_profile, payments_csv, bank_csv):
    contract = validate_profile(raw_profile)
    mapping = contract['mapping']
    sources = {'payments': payments_csv, 'bank': bank_csv}
    parsed, normalized, issues = {}, {}, []
    blocked_batches = set()
    for side, text in sources.items():
        headers, rows = table(text)
        if set(headers) != set(contract['schemas'][side]):
            missing = sorted(set(contract['schemas'][side]) - set(headers))
            added = sorted(set(headers) - set(contract['schemas'][side]))
            raise SafetyError(f'Schema drift in {side}: missing {missing}; new {added}. Re-teach or explicitly review a new mapping. No partial reconciliation.')
        parsed[side] = rows
        normalized[side] = []
        columns = mapping[side]
        ids = Counter(row['values'][columns['id']].strip() for row in rows)
        for row in rows:
            values = row['values']
            batch = values[columns['batch']].strip()
            currency = values[columns['currency']].strip()
            ident = values[columns['id']].strip()
            try:
                if not batch or not ident:
                    raise SafetyError('Missing record ID or batch reference.')
                if currency not in CURRENCIES:
                    raise SafetyError('Currency must be an explicit supported uppercase three-letter code.')
                if ids[ident] != 1:
                    raise SafetyError('Duplicate record ID. Every occurrence is quarantined, not silently deduplicated.')
                result = {'id': ident, 'batch': batch, 'currency': currency, 'record': row['record']}
                for role in ('gross', 'fee') if side == 'payments' else ('amount',):
                    result[role] = money(values[columns[role]].strip(), mapping['decimal_mark'])
                if side == 'payments' and result['fee'] < 0:
                    raise SafetyError('Negative fees are unsupported; review refunds or fee reversals explicitly.')
                normalized[side].append(result)
            except SafetyError as error:
                issues.append({'source': side, 'record': row['record'], 'id': ident, 'batch': batch,
                               'reason': str(error)})
                # A bad row must not disappear and let the remaining part of a batch match.
                if batch:
                    blocked_batches.add(batch)
    groups, transfers = defaultdict(list), defaultdict(list)
    for row in normalized['payments']:
        groups[row['batch']].append(row)
    for row in normalized['bank']:
        transfers[row['batch']].append(row)
    settlements = []
    keys = set(groups) | set(transfers) | blocked_batches
    for batch in sorted(keys):
        payments, bank = groups[batch], transfers[batch]
        currencies = {r['currency'] for r in payments + bank}
        gross = sum((r['gross'] for r in payments), Decimal('0.00'))
        fee = sum((r['fee'] for r in payments), Decimal('0.00'))
        expected = gross - fee
        received = sum((r['amount'] for r in bank), Decimal('0.00'))
        if batch in blocked_batches:
            status, reason = 'invalid', 'At least one source row in this batch was quarantined.'
        elif len(currencies) != 1:
            status, reason = 'currency_conflict', 'Different currencies must never be added or matched.'
        elif not payments:
            status, reason = 'orphan', 'Bank transfer has no corresponding payment records.'
        elif not bank:
            status, reason = 'missing', 'No bank transfer carries this exact batch reference.'
        elif len(bank) != 1:
            status, reason = 'ambiguous', 'Multiple bank transfers share this reference. No best guess was made.'
        elif expected != received:
            status, reason = 'mismatch', 'Gross minus fees does not equal the bank amount, even to the cent.'
        else:
            status, reason = 'matched', 'Exact batch reference, one currency, one bank transfer, exact net amount.'
        amounts = {'gross': str(gross), 'fees': str(fee), 'expected': str(expected),
                   'received': str(received), 'difference': str(received - expected)}
        if len(currencies) > 1:
            amounts = dict.fromkeys(amounts)
        settlements.append({'batch': batch, 'currency': next(iter(currencies)) if len(currencies) == 1 else 'MIXED',
                            'status': status, 'reason': reason, 'gross': str(gross), 'fees': str(fee),
                            **amounts,
                            'payment_records': [r['record'] for r in payments], 'bank_records': [r['record'] for r in bank]})
    ready = bool(settlements) and not issues and all(s['status'] == 'matched' for s in settlements)
    # Totals are per currency. No meaningless sum of USD and EUR is ever displayed.
    totals = {}
    for currency in sorted(CURRENCIES):
        rows = [r for r in normalized['payments'] if r['currency'] == currency]
        if rows:
            gross = sum((r['gross'] for r in rows), Decimal('0.00'))
            fees = sum((r['fee'] for r in rows), Decimal('0.00'))
            totals[currency] = {'gross': str(gross), 'fees': str(fees), 'net': str(gross - fees)}
    report = {'format': 'doze-close-report-v1', 'ready': ready, 'model_calls': 0,
              'profile_sha256': contract['sha256'], 'totals': totals,
              'settlements': settlements, 'issues': issues,
              'source_records': {side: len(rows) for side, rows in parsed.items()},
              'source_sha256': {side: hashlib.sha256(text.encode()).hexdigest() for side, text in sources.items()},
              'matched': sum(s['status'] == 'matched' for s in settlements),
              'exceptions': sum(s['status'] != 'matched' for s in settlements) + len(issues),
              'limitations': 'Exact shared settlement IDs only. Two-decimal currencies only. No date/amount fuzzy matching, tax advice, account access or payments. Human review required.'}
    report['sha256'] = fingerprint(report)
    return report


def csv_output(headers, rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(headers)
    for row in rows:
        safe = []
        for value in row:
            text = str(value)
            # Untrusted IDs and reasons can become spreadsheet formula payloads.
            if isinstance(value, str) and text.lstrip().startswith(('=', '+', '-', '@')):
                text = "'" + text
            safe.append(text)
        writer.writerow(safe)
    return stream.getvalue()


def packet(contract, payments_csv, bank_csv, approved_sha256):
    report = reconcile(contract, payments_csv, bank_csv)
    if approved_sha256 != report['sha256']:
        raise SafetyError('The approved report no longer matches these exact inputs and mapping. Reconcile and review again.')
    if not report['ready']:
        raise SafetyError('Handoff blocked: unresolved exceptions remain. Export the review evidence, not a clean handoff.')
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('reconciliation.csv', csv_output(
            ['batch', 'currency', 'gross', 'fees', 'net', 'bank_amount', 'payment_records', 'bank_records'],
            [[s['batch'], s['currency'], Decimal(s['gross']), Decimal(s['fees']), Decimal(s['expected']),
              Decimal(s['received']), ' '.join(map(str, s['payment_records'])), ' '.join(map(str, s['bank_records']))]
             for s in report['settlements']]))
        archive.writestr('audit.json', json.dumps(report, indent=2))
        archive.writestr('profile.json', json.dumps(validate_profile(contract), indent=2))
        archive.writestr('source-hashes.json', json.dumps(report['source_sha256'], indent=2))
        archive.writestr('READ-ME.txt', 'Doze reconciliation evidence, not tax advice or a bank statement.\n'
                          'Data record numbers are 1-based excluding the header. Source CSV contents are not included.\n'
                          'All included settlements matched exact references, currency and gross minus fees.\n'
                          'Human review of the column mapping and source completeness is still required.\n')
    return content.getvalue()

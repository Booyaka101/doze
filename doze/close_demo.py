"""Synthetic payment exports with explicitly known outcomes. No customer data."""
import csv
from decimal import Decimal
import io
import json
from pathlib import Path

from .engine import SafetyError
from .close import validate_profile

PAYMENT_HEADERS = ['Sale reference', 'Payout group', 'Customer paid', 'Processor fee', 'ISO currency']
BANK_HEADERS = ['Bank entry', 'Settlement reference', 'Money received', 'ISO currency']
MAPPING = {'name': 'Studio Friday close', 'decimal_mark': '.',
           'payments': dict(zip(('id', 'batch', 'gross', 'fee', 'currency'), PAYMENT_HEADERS)),
            'bank': dict(zip(('id', 'batch', 'amount', 'currency'), BANK_HEADERS))}


def recorded_profile():
    saved = json.loads(Path(__file__).with_name('close_recorded.json').read_text(encoding='utf-8'))
    return {'profile': validate_profile(saved['profile']), 'provenance': saved['provenance']}


def csv_text(headers, rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def demo(scenario='messy', week=1):
    if scenario not in {'clean', 'messy', 'penny', 'drift'} or type(week) is not int or not 1 <= week <= 52:
        raise SafetyError('Unknown synthetic close scenario.')
    payments, bank = [], []
    for group in range(1, 5):
        batch = f'PAY-W{week:02d}-{group:02d}'
        net = Decimal('0.00')
        for sale in range(1, 7):
            gross = Decimal(40 + week * 3 + group * 7 + sale * 2).quantize(Decimal('.01'))
            fee = (gross * Decimal('.029') + Decimal('.30')).quantize(Decimal('.01'))
            payments.append([f'SALE-{week:02d}-{group}-{sale}', batch, str(gross), str(fee), 'USD'])
            net += gross - fee
        bank.append([f'BANK-{week:02d}-{group}', batch, str(net), 'USD'])
    if scenario in {'messy', 'penny'}:
        bank[1][2] = str(Decimal(bank[1][2]) - Decimal('.01'))
    if scenario == 'messy':
        bank.append([f'BANK-{week:02d}-duplicate', bank[2][1], bank[2][2], 'USD'])
        bank.append([f'BANK-{week:02d}-unknown', f'UNEXPLAINED-W{week:02d}', '75.00', 'USD'])
    headers = list(PAYMENT_HEADERS)
    if scenario == 'drift':
        headers[2] = 'Customer paid (new format)'
    return {'scenario': scenario, 'week': week, 'synthetic': True,
            'payments_csv': csv_text(headers, payments), 'bank_csv': csv_text(BANK_HEADERS, bank),
            'description': 'Original synthetic fixtures. Not Stripe exports, customer records or bank statements.'}

import copy
import csv
from decimal import Decimal
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from doze.close import csv_output, money, packet, profile, reconcile, table, validate_profile
from doze.close_demo import BANK_HEADERS, MAPPING, PAYMENT_HEADERS, csv_text, demo
from doze.close_inference import compile_mapping
from doze.engine import SafetyError


class CloseTests(unittest.TestCase):
    def setUp(self):
        self.contract = profile(MAPPING, PAYMENT_HEADERS, BANK_HEADERS)
        self.data = demo('clean')

    def close(self, data=None, contract=None):
        data = data or self.data
        return reconcile(contract or self.contract, data['payments_csv'], data['bank_csv'])

    def change(self, side, record, column, value, data=None):
        data = copy.deepcopy(data or self.data)
        headers, rows = table(data[side + '_csv'])
        rows[record - 1]['values'][column] = value
        data[side + '_csv'] = csv_text(headers, [[r['values'][h] for h in headers] for r in rows])
        return data

    def test_clean_exact_arithmetic_and_provenance(self):
        result = self.close()
        self.assertTrue(result['ready'])
        self.assertEqual(result['matched'], 4)
        self.assertEqual(result['source_records'], {'payments': 24, 'bank': 4})
        first = result['settlements'][0]
        self.assertEqual(first['gross'], '342.00')
        self.assertEqual(first['fees'], '11.72')
        self.assertEqual(first['expected'], '330.28')
        self.assertEqual(first['payment_records'], list(range(1, 7)))
        self.assertEqual(result['totals']['USD']['gross'], '1620.00')
        self.assertEqual(len(result['source_sha256']['bank']), 64)

    def test_one_cent_is_a_blocking_difference(self):
        result = self.close(demo('penny'))
        self.assertFalse(result['ready'])
        mismatch = next(s for s in result['settlements'] if s['status'] == 'mismatch')
        self.assertEqual(mismatch['difference'], '-0.01')
        self.assertEqual(result['matched'], 3)

    def test_messy_fixture_has_three_honest_exceptions(self):
        result = self.close(demo('messy'))
        self.assertEqual(result['matched'], 2)
        self.assertEqual(result['exceptions'], 3)
        self.assertEqual({s['status'] for s in result['settlements']}, {'matched', 'mismatch', 'ambiguous', 'orphan'})

    def test_schema_drift_stops_everything(self):
        with self.assertRaisesRegex(SafetyError, 'Schema drift'):
            self.close(demo('drift'))

    def test_header_reordering_does_not_change_meaning(self):
        headers, rows = table(self.data['payments_csv'])
        headers.reverse()
        data = {**self.data, 'payments_csv': csv_text(headers, [[r['values'][h] for h in headers] for r in rows])}
        self.assertTrue(self.close(data)['ready'])

    def test_extra_unreviewed_column_is_drift(self):
        data = {**self.data, 'bank_csv': self.data['bank_csv'].replace('ISO currency\n', 'ISO currency,extra\n').replace('USD\n', 'USD,new\n')}
        with self.assertRaisesRegex(SafetyError, 'Schema drift'):
            self.close(data)

    def test_duplicate_sale_ids_quarantine_every_occurrence_and_block_batches(self):
        data = self.change('payments', 7, 'Sale reference', 'SALE-01-1-1')
        result = self.close(data)
        self.assertEqual(len(result['issues']), 2)
        invalid = [s for s in result['settlements'] if s['status'] == 'invalid']
        self.assertEqual(len(invalid), 2)
        self.assertFalse(result['ready'])

    def test_duplicate_bank_id_cannot_be_a_match(self):
        result = self.close(self.change('bank', 2, 'Bank entry', 'BANK-01-1'))
        self.assertEqual(len(result['issues']), 2)
        self.assertFalse(result['ready'])

    def test_missing_bank_transfer_is_not_fuzzily_matched_by_amount(self):
        data = self.change('bank', 1, 'Settlement reference', 'different-reference')
        result = self.close(data)
        self.assertIn('missing', {s['status'] for s in result['settlements']})
        self.assertIn('orphan', {s['status'] for s in result['settlements']})

    def test_mixed_currencies_are_never_summed_for_a_settlement(self):
        result = self.close(self.change('payments', 1, 'ISO currency', 'EUR'))
        mixed = next(s for s in result['settlements'] if s['status'] == 'currency_conflict')
        self.assertIsNone(mixed['expected'])
        self.assertIsNone(mixed['received'])
        self.assertEqual(set(result['totals']), {'USD', 'EUR'})
        self.assertFalse(result['ready'])

    def test_unknown_currency_is_quarantined_not_assumed_usd(self):
        result = self.close(self.change('payments', 1, 'ISO currency', 'JPY'))
        self.assertEqual(len(result['issues']), 1)
        self.assertEqual(result['settlements'][0]['status'], 'invalid')

    def test_bad_amount_never_disappears_to_allow_partial_batch_match(self):
        result = self.close(self.change('payments', 1, 'Customer paid', 'NaN'))
        self.assertEqual(result['settlements'][0]['status'], 'invalid')
        self.assertFalse(result['ready'])

    def test_missing_batch_blocks_packet_even_if_other_rows_match(self):
        result = self.close(self.change('payments', 1, 'Payout group', ''))
        self.assertTrue(result['issues'])
        self.assertFalse(result['ready'])

    def test_negative_fees_need_review(self):
        result = self.close(self.change('payments', 1, 'Processor fee', '-1.00'))
        self.assertFalse(result['ready'])
        self.assertIn('Negative fees', result['issues'][0]['reason'])

    def test_refund_can_be_negative_gross_without_float_rounding(self):
        data = self.change('payments', 1, 'Customer paid', '-52.00')
        data = self.change('bank', 1, 'Money received', '226.28', data)
        self.assertTrue(self.close(data)['ready'])

    def test_decimal_comma_requires_explicit_contract(self):
        raw = copy.deepcopy(MAPPING); raw['decimal_mark'] = ','
        contract = profile(raw, PAYMENT_HEADERS, BANK_HEADERS)
        data = dict(self.data)
        for side, roles in [('payments', ['Customer paid', 'Processor fee']), ('bank', ['Money received'])]:
            headers, rows = table(data[side + '_csv'])
            for row in rows:
                for role in roles:
                    row['values'][role] = row['values'][role].replace('.', ',')
            data[side + '_csv'] = csv_text(headers, [[r['values'][h] for h in headers] for r in rows])
        self.assertTrue(self.close(data, contract)['ready'])
        self.assertFalse(self.close(data)['ready'])

    def test_money_rejects_ambiguous_precision_exponents_and_symbols(self):
        for value in ['1,000.00', '$10', '1e3', '0.001', 'NaN', 'Infinity', '', '+3.00', '1_000', '1.']:
            with self.subTest(value=value), self.assertRaises(SafetyError):
                money(value, '.')
        self.assertEqual(money('0.10', '.') + money('0.20', '.'), Decimal('0.30'))

    def test_empty_ragged_duplicate_header_and_malformed_csv_rejected(self):
        for value in ['', 'x,x\n1,2\n', 'x,y\n1\n', 'x\n', 'x,y\n"unterminated,1']:
            with self.subTest(value=value), self.assertRaises(SafetyError):
                table(value)

    def test_multiline_record_provenance_is_logical_not_physical_line(self):
        headers, rows = table('id,note\n1,"first\nsecond"\n2,last\n')
        self.assertEqual(headers, ['id', 'note'])
        self.assertEqual([r['record'] for r in rows], [1, 2])

    def test_bom_and_crlf_are_supported(self):
        data = {**self.data, 'payments_csv': '\ufeff' + self.data['payments_csv'].replace('\n', '\r\n')}
        self.assertTrue(self.close(data)['ready'])

    def test_same_column_cannot_have_multiple_meanings(self):
        raw = copy.deepcopy(MAPPING); raw['payments']['fee'] = raw['payments']['gross']
        with self.assertRaisesRegex(SafetyError, 'two roles'):
            profile(raw, PAYMENT_HEADERS, BANK_HEADERS)

    def test_model_cannot_invent_a_column(self):
        raw = copy.deepcopy(MAPPING); raw['payments']['gross'] = 'invented'
        with self.assertRaises(SafetyError):
            profile(raw, PAYMENT_HEADERS, BANK_HEADERS)

    def test_import_recomputes_profile_identity(self):
        raw = copy.deepcopy(self.contract); raw['sha256'] = 'trusted-looking-fake'
        self.assertEqual(validate_profile(raw)['sha256'], self.contract['sha256'])

    def test_clean_packet_has_audit_profile_and_formula_safe_csv(self):
        result = self.close()
        raw = packet(self.contract, self.data['payments_csv'], self.data['bank_csv'], result['sha256'])
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(set(archive.namelist()), {'reconciliation.csv', 'audit.json', 'profile.json', 'source-hashes.json', 'READ-ME.txt'})
            self.assertEqual(json.loads(archive.read('audit.json'))['sha256'], result['sha256'])
            self.assertNotIn('payments.csv', archive.namelist())
        self.assertIn("'=SUM", csv_output(['id'], [['=SUM(A1)']]))
        self.assertIn("' @payload", csv_output(['id'], [[' @payload']]))

    def test_changed_input_cannot_use_previously_approved_report(self):
        result = self.close()
        data = demo('clean', 2)
        with self.assertRaisesRegex(SafetyError, 'approved report'):
            packet(self.contract, data['payments_csv'], data['bank_csv'], result['sha256'])

    def test_unresolved_exception_cannot_export_clean_packet(self):
        data = demo('penny'); result = self.close(data)
        with self.assertRaisesRegex(SafetyError, 'unresolved exceptions'):
            packet(self.contract, data['payments_csv'], data['bank_csv'], result['sha256'])

    def test_deterministic_reuse_needs_no_network(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Network forbidden')):
            for week in range(1, 53):
                result = self.close(demo('clean', week))
                self.assertTrue(result['ready'])
                self.assertEqual(result['matched'], 4)
                self.assertEqual(result['model_calls'], 0)

    def test_compiler_receives_only_headers_and_validates_result(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
                'message': {'content': json.dumps(MAPPING)}}) as call:
            result = compile_mapping(PAYMENT_HEADERS, BANK_HEADERS, 'local')
        sent = json.loads(call.call_args.args[1]['messages'][1]['content'])
        self.assertEqual(set(sent), {'payment_headers', 'bank_headers', 'decimal_mark', 'user_hint'})
        self.assertEqual(result['profile'], self.contract)

    def test_compiler_cannot_silently_change_decimal_mark(self):
        with patch('doze.compiler.models', return_value=['local']), patch('doze.compiler.request_json', return_value={
                'message': {'content': json.dumps(MAPPING)}}), self.assertRaisesRegex(SafetyError, 'decimal mark'):
            compile_mapping(PAYMENT_HEADERS, BANK_HEADERS, 'local', ',')

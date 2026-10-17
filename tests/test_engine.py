"""Independent G1 expectations; discovery files are parser fixtures, never fresh reads.

Synthetic review cases below are locally constructed tests, not business decisions.
"""
import copy
from datetime import date
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOT = Path(os.environ.get('PROJECT_D_IMPLEMENTATION_ROOT', ROOT))
sys.path.insert(0, str(ROOT / 'skills/travel-expense-claim/scripts'))
import source_io

SPEC = importlib.util.spec_from_file_location('g1_engine_under_test', IMPLEMENTATION_ROOT / 'skills/travel-expense-claim/scripts/engine.py')
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)
CLOCK = {'date': '2026-11-15', 'timezone': 'Europe/Amsterdam'}


def synthetic_review():
    person = {'Employee ID': 'SYN-EMP', 'Administration reviewer': 'SYN-ADMIN', 'Budget owner': 'SYN-BUDGET',
              'Supervisor': 'SYN-SUP', 'Director': 'SYN-DIR', 'Department': 'Synthetic', 'Project': 'Test', 'Budget period': '2026'}
    trip = {'Trip reference': 'SYN-TRIP', 'Trip revision': '1', 'Permit reference': '', 'Permit revision': '',
            'Business purpose': 'Synthetic test journey', 'Client': 'Test', 'Schedule coverage': 'Test', 'Alternatives considered': 'Test'}
    ledger, packets = [], []
    for role, actor in [('administration', 'SYN-ADMIN'), ('budget_owner', 'SYN-BUDGET'), ('supervisor', 'SYN-SUP')]:
        decision = 'SYN-' + role
        ledger.append({'Decision reference': decision, 'Arrival batch': '1', 'Subject type': 'claim',
                       'Subject reference': 'SYN-CLAIM', 'Revision': '1', 'Review roles': role, 'Reviewer': actor,
                       'Source revisions': 'DW-D-2\nPOL-2026.2\nSRC-D-3', 'Decision time (UTC)': '2026-09-03T12:00:00Z',
                       'Outcome': 'approve', 'Reason': 'Synthetic supported approval', 'Repair requested': '',
                       '_source_id': 'synthetic-test', '_locator': decision})
        packets.append(dict(trip, **{'Decision reference': decision, 'Employee ID': 'SYN-EMP',
                                    'Policy revision': 'POL-2026.2', 'Expense references': 'SYN-COST',
                                    'Budget record references': '', 'Travel cancellation references': '',
                                    'Reviewed estimate (EUR)': '', 'Budget owner position': 'Approved'}))
    return person, trip, {'Review ledger': ledger, 'Review packets': packets, 'Budget': []}


def review(person, trip, tables):
    return engine.review('claim', 'SYN-CLAIM', 1, trip, person, 10000, ['SYN-COST'], tables, 2, date(2026, 11, 15))


class ActualG1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        discovery = ROOT / 'artifacts/discovery'
        claims = []
        for sid, filename in [('initial', 'claims-initial.pdf'), ('updates', 'claims-updates.pdf')]:
            claims.extend(source_io._pdf(discovery / '2026-10-17' / filename, sid, 'SRC-D-3')[0])
        cls.data = {'claims': claims, 'receipts': source_io._pdf(discovery / '2026-10-16/receipts.pdf', 'receipts', 'SRC-D-3')[0],
                    'tables': source_io._workbook(discovery / '2026-10-16/travel-registers.xlsx', 'SRC-D-3')[0]}
        cls.states = {b: engine.reduce_batch(cls.data, b, CLOCK) for b in (1, 2)}

    def test_connected_path_keeps_entitlement_acceptance_and_payment_distinct(self):
        first, second = self.states[1], self.states[2]
        a = {c['claim_id']: c for c in first['claims']}
        b = {c['claim_id']: c for c in second['claims']}
        self.assertEqual(len(a), 120)
        self.assertEqual(set(a), set(b))
        self.assertEqual((a['C01']['allowed_cents'], a['C01']['paid_cents'], a['C01']['balance_cents']), (10000, 0, 10000))
        self.assertFalse(a['C01']['closure_candidate'])
        self.assertEqual((b['C01']['allowed_cents'], b['C01']['paid_cents'], b['C01']['balance_cents']), (10000, 10000, 0))
        self.assertTrue(b['C01']['closure_candidate'])
        self.assertIsNone(b['C01']['next_owner'])
        self.assertEqual(b['C01']['status'], 'closed-reimbursed')
        request = next(r for r in second['requests'] if r['claim_id'] == 'C01')
        self.assertEqual(request['amount_cents'], 10000)
        self.assertIn('F-C01-1', request['event_ids'])
        self.assertIn('F-C01-1', second['admitted_event_ids'])
        self.assertEqual(b['C02']['allowed_cents'], 54000)
        permit = next(p for p in first['permits'] if p['permit_id'] == 'P02')
        self.assertEqual((permit['estimate_cents'], permit['status']), (110000, 'approved'))
        director = [r for r in first['decisions'] if r['Subject reference'] == 'P02' and r['Review roles'] == 'director']
        self.assertEqual(len(director), 1)
        self.assertTrue(director[0]['admitted'])
        self.assertIn(director[0]['Decision reference'], permit['decision_ids'])
        self.assertNotIn(director[0]['Decision reference'], b['C02']['decision_ids'])

    def test_missing_merchant_proof_holds_only_dependent_claim_work(self):
        for state in self.states.values():
            c = next(c for c in state['claims'] if c['claim_id'] == 'C114')
            lines = {line['cost_id']: line for line in c['lines']}
            self.assertEqual((lines['COST-114-1']['allowed_cents'], lines['COST-114-1']['status']), (2000, 'supported'))
            self.assertIsNone(lines['COST-114-2']['allowed_cents'])
            self.assertIn('merchant_payment_missing_or_ambiguous', lines['COST-114-2']['findings'])
            self.assertIsNone(c['allowed_cents'])
            self.assertIsNone(c['balance_cents'])
            self.assertEqual(c['next_owner'], 'EMP-03 / Administration')
            self.assertTrue(c['issue_record_ids'])
            self.assertFalse(any(r['claim_id'] == 'C114' for r in state['requests']))
            self.assertTrue(any(c['claim_id'] == 'C01' and c['approval_status'] == 'approved' for c in state['claims']))

    def test_partial_payment_overpayment_and_withdrawal(self):
        claims = {c['claim_id']: c for c in self.states[2]['claims']}
        self.assertEqual((claims['C16']['paid_cents'], claims['C16']['balance_cents']), (4000, 6000))
        self.assertFalse(claims['C16']['closure_candidate'])
        self.assertEqual(claims['C16']['next_owner'], 'Finance')
        self.assertEqual((claims['C20']['paid_cents'], claims['C20']['balance_cents']), (11000, -1000))
        self.assertEqual((claims['C20']['status'], claims['C20']['next_owner']), ('held', 'Finance'))
        self.assertIn('C20:r1:overpayment', claims['C20']['issue_record_ids'])
        self.assertEqual((claims['C13']['status'], claims['C13']['allowed_cents'], claims['C13']['paid_cents']), ('withdrawn', 0, 0))
        self.assertFalse(any(r['claim_id'] == 'C13' for r in self.states[2]['requests']))

    def test_independent_cancellation_has_separate_identity_without_fake_claim(self):
        first = next(c for c in self.states[1]['travel_cancellations'] if c['cancellation_id'] == 'TC122')
        second = next(c for c in self.states[2]['travel_cancellations'] if c['cancellation_id'] == 'TC122')
        self.assertEqual((first['status'], second['status']), ('requested', 'confirmed'))
        self.assertEqual(second['affected_claim_ids'], [])
        self.assertEqual(second['financial_status'], 'no-financial-effect')
        self.assertEqual(second['admitted_cancellation_event_ids'], ['TC122-requested', 'TC122-confirmed'])
        self.assertFalse(any(c['claim_id'] == 'C122' for c in self.states[2]['claims']))
        self.assertTrue(set(second['admitted_cancellation_event_ids']).isdisjoint(self.states[2]['admitted_event_ids']))

    def test_synthetic_tied_cancellation_confirmation_is_invalid(self):
        data = copy.deepcopy(self.data)
        rows = data['tables']['Travel cancellations']
        requested = next(r for r in rows if r['Cancellation activity reference'] == 'TC122-requested')
        confirmed = next(r for r in rows if r['Cancellation activity reference'] == 'TC122-confirmed')
        # Sort initiation before confirmation even at the tied timestamp, so
        # rejection demonstrates the strict-time rule rather than missing state.
        requested['Cancellation activity reference'] = 'SYN-A-requested'
        confirmed['Cancellation activity reference'] = 'SYN-B-confirmed'
        confirmed['Initiation activity reference'] = 'SYN-A-requested'
        confirmed['Activity time (UTC)'] = requested['Activity time (UTC)']
        confirmed['Effective time (UTC)'] = requested['Activity time (UTC)']
        confirmed['Arrival batch'] = requested['Arrival batch']
        state = engine.reduce_batch(data, 2, CLOCK)
        c = next(c for c in state['travel_cancellations'] if c['cancellation_id'] == 'TC122')
        self.assertEqual(c['status'], 'requested')
        self.assertEqual(c['admitted_cancellation_event_ids'], ['SYN-A-requested'])
        event = next(e for e in state['cancellation_events'] if e['Cancellation activity reference'] == 'SYN-B-confirmed')
        self.assertFalse(event['admitted'])
        self.assertIn('strictly later', event['validation_error'])
        self.assertTrue(any('TC122' == i['subject_id'] for i in state['issues']))

    def test_missing_finance_history_fails_instead_of_substituting_zero(self):
        data = copy.deepcopy(self.data)
        data['tables']['Finance activity'] = []
        with self.assertRaisesRegex(source_io.SourceError, 'Unknown paid history.*cannot seal'):
            engine.reduce_batch(data, 2, CLOCK)


class SyntheticAuthorityTests(unittest.TestCase):
    def test_all_same_batch_ties_valid_for_exact_subject_and_revision(self):
        person, trip, tables = synthetic_review()
        self.assertEqual(review(person, trip, tables)['outcome'], 'approved')
        # The same otherwise valid approvals cannot authorize another revision.
        result = engine.review('claim', 'SYN-CLAIM', 2, trip, person, 10000, ['SYN-COST'], tables, 2, date(2026, 11, 15))
        self.assertNotEqual(result['outcome'], 'approved')

    def test_cross_batch_tie_and_backwards_stage_invalid(self):
        for mode in ('cross-batch', 'backwards'):
            with self.subTest(mode=mode):
                person, trip, tables = synthetic_review()
                if mode == 'cross-batch':
                    tables['Review ledger'][1]['Arrival batch'] = '2'
                    tables['Review ledger'][2]['Arrival batch'] = '2'
                else:
                    tables['Review ledger'][1]['Decision time (UTC)'] = '2026-09-03T11:59:59Z'
                result = review(person, trip, tables)
                self.assertNotEqual(result['outcome'], 'approved')
                self.assertTrue(any('sequence' in p for p in result['problems']))

    def test_wrong_actor_source_revision_or_packet_cannot_authorize(self):
        for mode in ('actor', 'source-version', 'policy-packet', 'trip-packet'):
            with self.subTest(mode=mode):
                person, trip, tables = synthetic_review()
                if mode == 'actor':
                    tables['Review ledger'][1]['Reviewer'] = 'UNAUTHORIZED'
                elif mode == 'source-version':
                    tables['Review ledger'][1]['Source revisions'] = 'DW-D-2\nPOL-2026.1\nSRC-D-3'
                elif mode == 'policy-packet':
                    tables['Review packets'][1]['Policy revision'] = 'POL-2026.1'
                else:
                    tables['Review packets'][1]['Trip revision'] = '2'
                result = review(person, trip, tables)
                self.assertNotEqual(result['outcome'], 'approved')
                self.assertFalse(result['records'][1]['admitted'])
                self.assertTrue(result['records'][1]['validation_errors'])

    def test_combined_budget_supervisor_response_requires_same_authorized_person(self):
        for same_person in (True, False):
            with self.subTest(same_person=same_person):
                person, trip, tables = synthetic_review()
                if same_person:
                    person['Supervisor'] = person['Budget owner']
                tables['Review ledger'][1]['Review roles'] = 'budget_owner\nsupervisor'
                tables['Review ledger'].pop()
                tables['Review packets'].pop()
                result = review(person, trip, tables)
                self.assertEqual(result['outcome'] == 'approved', same_person)
                # A combined response for a different subject cannot approve this one.
                tables['Review ledger'][1]['Subject reference'] = 'SYN-OTHER'
                self.assertNotEqual(review(person, trip, tables)['outcome'], 'approved')


if __name__ == '__main__':
    unittest.main()

"""Independent four-batch expectations from the retained supplied records.

Mutation cases are explicitly synthetic adversarial inputs, not new business facts.
"""
import copy
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOT = Path(os.environ.get('PROJECT_D_IMPLEMENTATION_ROOT', ROOT))
SCRIPTS = IMPLEMENTATION_ROOT / 'skills/travel-expense-claim/scripts'
sys.path.insert(0, str(SCRIPTS))
import source_io
from workflow import reduce_batches

CLOCK = {'date': '2026-11-15', 'timezone': 'Europe/Amsterdam'}
RUN = IMPLEMENTATION_ROOT / 'artifacts/runs/g1-reviewed-20261017'


def claim(state, identity):
    return next(c for c in state['claims'] if c['claim_id'] == identity)


def request(state, identity):
    return next(r for r in state['requests'] if r['request_id'] == identity)


def cancellation(state, identity):
    return next(c for c in state['travel_cancellations'] if c['cancellation_id'] == identity)


def event(data, identity):
    return next(e for e in data['tables']['Finance activity'] if e['Activity reference'] == identity)


class ActualFourBatchBusinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = source_io.normalize(RUN)
        cls.states = reduce_batches(cls.data, 4, CLOCK)

    def test_same_total_replacement_trip_requires_current_review_and_source_basis(self):
        old, current, final = (claim(self.states[b-1], 'C09') for b in (2, 3, 4))
        self.assertEqual((old['trip_id'], current['trip_id'], old['allowed_cents'], current['allowed_cents']),
                         ('T09', 'T09B', 8000, 8000))
        self.assertTrue(set(old['decision_ids']).isdisjoint(current['decision_ids']))
        self.assertEqual(current['source_refs'], [{'source_id': 'updates', 'locator': 'page 1, card 1'}])
        self.assertEqual(current['lines'][0]['cost_id'], 'COST-09B')
        revision = next(r for r in self.states[2]['revision_history'] if r['claim_id'] == 'C09')
        self.assertIn('trip_id', revision['changed_fields'])
        self.assertEqual(set(revision['invalidated_decision_ids']), set(old['decision_ids']))
        self.assertEqual((request(self.states[3], 'REQ-C09')['trip_id'], final['paid_cents'], final['status']),
                         ('T09B', 8000, 'closed-reimbursed'))
        self.assertTrue(any(h['claim_id'] == 'C09' and h['revision'] == 1 for h in self.states[3]['claim_history']))

    def test_amount_only_exception_cannot_resolve_cancellation_or_current_reviews(self):
        middle = claim(self.states[2], 'C19')
        self.assertEqual((middle['revision'], middle['lines'][0]['arithmetic_cents'], middle['paid_cents']), (2, 8000, 10000))
        self.assertIsNone(middle['allowed_cents'])
        self.assertIsNone(middle['balance_cents'])
        self.assertIn('travel_cancellation', middle['lines'][0]['findings'])
        self.assertEqual(middle['lines'][0]['exception']['covered_issues'], [])
        self.assertEqual(middle['decision_ids'], [])
        self.assertTrue(any('review_authority' in i for i in middle['issue_record_ids']))
        final = claim(self.states[3], 'C19')
        original_request = request(self.states[3], 'REQ-C19')
        self.assertEqual((final['revision'], final['allowed_cents'], final['paid_cents'], final['balance_cents'], final['status']),
                         (3, 8000, 8000, 0, 'closed-reimbursed'))
        self.assertEqual(final['lines'][0]['original_arithmetic_cents'], 10000)
        self.assertEqual(final['lines'][0]['resolved_findings'], ['travel_cancellation'])
        self.assertEqual((original_request['original_amount_cents'], original_request['amount_cents'], original_request['resolution_event_id']),
                         (10000, 8000, 'F-C19-4'))
        self.assertEqual(original_request['refunded_by_settlement'], {'F-C19-1': 2000})
        self.assertEqual(cancellation(self.states[3], 'TC019')['financial_status'], 'resolved')

    def test_first_acceptance_after_cancellation_can_close_without_extra_resolution(self):
        state = self.states[3]
        c, r, process = claim(state, 'C121'), request(state, 'REQ-C121'), cancellation(state, 'TC121')
        self.assertGreater(r['accepted_at'], process['confirmed_at'])
        self.assertFalse(r['resolution_required'])
        self.assertIsNone(r['resolution_event_id'])
        self.assertEqual((c['allowed_cents'], c['paid_cents'], c['balance_cents'], c['status']), (2000, 2000, 0, 'closed-reimbursed'))
        self.assertEqual(process['target_type'], 'permit')
        travel = next(t for t in state['travel_bases'] if t['trip_id'] == 'T121')
        self.assertEqual((travel['status'], travel['permission']), ('active', 'retired'))

    def test_late_transfer_keeps_original_request_basis_after_trip_reassignment(self):
        state = self.states[3]
        c, r = claim(state, 'C18'), request(state, 'REQ-C18')
        self.assertEqual((c['revision'], c['trip_id'], r['revision'], r['trip_id']), (2, 'T18B', 1, 'T18'))
        self.assertEqual((r['original_amount_cents'], r['amount_cents'], r['net_paid_cents']), (10000, 0, 10000))
        self.assertIn('F-C18-3', state['admitted_event_ids'])
        self.assertEqual(c['unreconciled_paid_cents'], 10000)
        self.assertEqual(c['status'], 'held')
        self.assertFalse(c['closure_candidate'])
        self.assertIsNone(c['balance_cents'])
        self.assertEqual(c['payable_cents'], 0)
        self.assertTrue(any('prior_request_basis:REQ-C18' in i for i in c['issue_record_ids']))
        self.assertEqual(next(t for t in state['travel_bases'] if t['trip_id'] == 'T18B')['status'], 'active')

    def test_prepaid_cost_excluded_from_final_claim_without_duplicate_obligation(self):
        state = self.states[3]
        c = claim(state, 'C24')
        old_line = next(l for l in c['lines'] if l['cost_id'] == 'COST-03')
        self.assertEqual((old_line['status'], old_line['allowed_cents'], old_line['original_request_id']), ('excluded', 0, 'REQ-C03'))
        self.assertEqual((claim(state, 'C03')['paid_cents'], c['allowed_cents'], c['paid_cents']), (20000, 5000, 5000))
        self.assertEqual(request(state, 'REQ-C24')['cost_ids'], ['COST-24'])
        self.assertEqual(request(state, 'REQ-C24')['amount_cents'], 5000)

    def test_refund_zero_balance_still_requires_explicit_finance_resolution(self):
        before, after = claim(self.states[2], 'C20'), claim(self.states[3], 'C20')
        self.assertEqual((before['paid_cents'], before['balance_cents'], before['status']), (10000, 0, 'held'))
        self.assertFalse(before['closure_candidate'])
        self.assertIn('C20:r1:finance_resolution:REQ-C20', before['issue_record_ids'])
        self.assertEqual(request(self.states[2], 'REQ-C20')['refunded_by_settlement'], {'F-C20-1': 1000})
        self.assertEqual((after['status'], request(self.states[3], 'REQ-C20')['resolution_event_id']), ('closed-reimbursed', 'F-C20-3'))

    def test_exact_redeliveries_have_no_money_or_cancellation_effect(self):
        early, final = self.states[1], self.states[3]
        self.assertEqual((claim(early, 'C01')['paid_cents'], claim(final, 'C01')['paid_cents']), (10000, 10000))
        self.assertEqual(final['admitted_event_ids'].count('F-C01-1'), 1)
        self.assertEqual(request(final, 'REQ-C01')['event_ids'].count('F-C01-1'), 1)
        a, b = cancellation(early, 'TC122'), cancellation(final, 'TC122')
        self.assertEqual(a['admitted_cancellation_event_ids'], b['admitted_cancellation_event_ids'])
        self.assertEqual((b['affected_claim_ids'], b['original_request_ids'], b['financial_status']), ([], [], 'no-financial-effect'))
        self.assertFalse(any(c['claim_id'] == 'C122' for c in final['claims']))
        self.assertTrue(set(b['admitted_cancellation_event_ids']).isdisjoint(final['admitted_event_ids']))

    def test_incomplete_claim_retains_supported_line_and_unknown_total(self):
        for state in self.states:
            c = claim(state, 'C114')
            lines = {l['cost_id']: l for l in c['lines']}
            self.assertEqual((lines['COST-114-1']['allowed_cents'], c['supported_cents']), (2000, 2000))
            self.assertIsNone(lines['COST-114-2']['allowed_cents'])
            self.assertIsNone(c['allowed_cents'])
            self.assertIsNone(c['balance_cents'])
            self.assertEqual(c['payable_cents'], 0)
            self.assertFalse(any(r['claim_id'] == 'C114' for r in state['requests']))

    def test_source_thresholds_unit_caps_and_line_half_up_rounding(self):
        state = self.states[0]
        expected = {'C05':100000, 'C06':100001, 'C07':30000, 'C99':99999, 'C100':100000, 'C101':100001,
                    'C102':14999, 'C103':15000, 'C104':15000, 'C105':3999, 'C106':4000, 'C107':4000,
                    'C108':208, 'C109':208}
        for identity, cents in expected.items():
            with self.subTest(claim=identity):
                self.assertEqual(claim(state, identity)['allowed_cents'], cents)
        for identity in ('C05','C99','C100'):
            self.assertFalse(any('director' in d for d in claim(state, identity)['decision_ids']))
        for identity in ('C06','C101'):
            self.assertEqual(sum('director' in d for d in claim(state, identity)['decision_ids']), 1)
        self.assertEqual([l['allowed_cents'] for l in claim(state, 'C108')['lines']], [104,104])
        self.assertEqual([l['allowed_cents'] for l in claim(state, 'C109')['lines']], [104,104])
        self.assertEqual(next(r['units'] for r in self.data['receipts'] if r['cost_id']=='COST-07'), 2)


class SyntheticAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual = source_io.normalize(RUN)

    def data(self):
        return copy.deepcopy(self.actual)

    def test_wrong_finance_actor_payee_and_currency_cannot_admit_transfer(self):
        for field in ('Finance officer','Payee ID','Currency'):
            with self.subTest(field=field):
                data=self.data()
                event(data,'F-C01-1')[field]='SYN-WRONG'
                state=reduce_batches(data,2,CLOCK)[-1]
                self.assertNotIn('F-C01-1',state['admitted_event_ids'])
                self.assertEqual(claim(state,'C01')['paid_cents'],0)
                observation=next(e for e in state['finance_events'] if e['Activity reference']=='F-C01-1')
                self.assertIn('Wrong Finance actor, payee or currency',observation['validation_error'])
                self.assertTrue(any(i['subject_id']=='C01' and 'finance_event' in i['fact'] for i in state['issues']))

    def test_orphan_finance_event_rechecked_only_when_original_basis_arrives(self):
        data=self.data()
        event(data,'F-C01-accepted')['Arrival batch']='3'
        states=reduce_batches(data,3,CLOCK)
        self.assertNotIn('F-C01-1',states[1]['admitted_event_ids'])
        self.assertEqual(claim(states[1],'C01')['paid_cents'],0)
        self.assertIn('F-C01-1',states[2]['admitted_event_ids'])
        self.assertEqual(claim(states[2],'C01')['paid_cents'],10000)
        self.assertEqual(request(states[2],'REQ-C01')['event_ids'].count('F-C01-1'),1)

    def test_refund_cannot_exceed_unrecovered_part_of_original_settlement(self):
        data=self.data()
        duplicate=copy.deepcopy(event(data,'F-C20-2'))
        duplicate.update({'Activity reference':'SYN-EXCESS-REFUND','Amount (EUR)':'100.01','_locator':'synthetic refund after supplied EUR10 refund'})
        data['tables']['Finance activity'].append(duplicate)
        state=reduce_batches(data,3,CLOCK)[-1]
        self.assertIn('F-C20-2',state['admitted_event_ids'])
        self.assertNotIn('SYN-EXCESS-REFUND',state['admitted_event_ids'])
        self.assertEqual(claim(state,'C20')['paid_cents'],10000)
        bad=next(e for e in state['finance_events'] if e['Activity reference']=='SYN-EXCESS-REFUND')
        self.assertIn('exceeds unrecovered',bad['validation_error'])

    def test_invalid_exception_actor_or_cancellation_identity_cannot_release_cost(self):
        for field in ('actor','cancellation_id'):
            with self.subTest(field=field):
                data=self.data()
                card=next(c for c in data['claims'] if c['claim_id']=='C121' and c['revision']==2)
                card['exception'][field]='SYN-WRONG'
                state=reduce_batches(data,4,CLOCK)[-1]
                c=claim(state,'C121')
                self.assertIn('invalid_scoped_exception',c['lines'][0]['findings'])
                self.assertIn('travel_cancellation',c['lines'][0]['findings'])
                self.assertIsNone(c['allowed_cents'])
                self.assertEqual(c['paid_cents'],0)
                self.assertFalse(c['closure_candidate'])

    def test_conflicting_cancellation_redelivery_holds_without_erasing_original(self):
        data=self.data()
        redelivery=next(e for e in data['tables']['Travel cancellations'] if e['Cancellation activity reference']=='TC122-confirmed' and e['Arrival batch']=='4')
        redelivery['Business reason']='Synthetic contradictory immutable payload'
        state=reduce_batches(data,4,CLOCK)[-1]
        c=cancellation(state,'TC122')
        self.assertEqual(c['status'],'confirmed')
        self.assertEqual(c['confirmed_at'],'2026-09-12T09:00:00Z')
        self.assertEqual(c['admitted_cancellation_event_ids'],['TC122-requested','TC122-confirmed'])
        self.assertTrue(c['issue_record_ids'])
        self.assertTrue(any('Conflicting redelivery' in i['reason'] for i in state['issues'] if i['subject_id']=='TC122'))

    def test_orphan_cancellation_confirmation_waits_for_later_request_arrival(self):
        data=self.data()
        for e in data['tables']['Travel cancellations']:
            if e['Cancellation activity reference']=='TC122-requested':e['Arrival batch']='3'
            elif e['Cancellation activity reference']=='TC122-confirmed' and e['Arrival batch']=='2':e['Arrival batch']='1'
        states=reduce_batches(data,3,CLOCK)
        self.assertFalse(any(c['cancellation_id']=='TC122' for c in states[0]['travel_cancellations']))
        self.assertTrue(any(i['subject_id']=='TC122' for i in states[0]['issues']))
        final=cancellation(states[2],'TC122')
        self.assertEqual((final['status'],final['financial_status']),('confirmed','no-financial-effect'))
        self.assertEqual(final['admitted_cancellation_event_ids'],['TC122-requested','TC122-confirmed'])
        self.assertFalse(any(i['subject_id']=='TC122' for i in states[2]['issues']))

    def test_equal_time_confirmation_cannot_establish_business_cancellation(self):
        data=self.data()
        rows=data['tables']['Travel cancellations']
        first=next(e for e in rows if e['Cancellation activity reference']=='TC122-requested')
        confirmed=next(e for e in rows if e['Cancellation activity reference']=='TC122-confirmed')
        confirmed['Activity time (UTC)']=first['Activity time (UTC)']
        confirmed['Effective time (UTC)']=first['Activity time (UTC)']
        state=reduce_batches(data,2,CLOCK)[-1]
        c=cancellation(state,'TC122')
        self.assertEqual(c['status'],'requested')
        self.assertIsNone(c['confirmed_at'])
        self.assertEqual(c['admitted_cancellation_event_ids'],['TC122-requested'])
        self.assertTrue(c['issue_record_ids'])

    def test_missing_paid_history_fails_instead_of_inventing_zero(self):
        data=self.data()
        data['tables']['Finance activity']=[]
        with self.assertRaisesRegex(source_io.SourceError,'Unknown paid history.*cannot seal'):
            reduce_batches(data,4,CLOCK)


if __name__=='__main__':
    unittest.main()

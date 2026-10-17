"""Focused source-backed closure and original-versus-replacement authority checks.

Added review rows below are synthetic test fixtures only, never scenario evidence.
"""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOT = Path(os.environ.get('PROJECT_D_IMPLEMENTATION_ROOT', ROOT))
sys.path.insert(0, str(IMPLEMENTATION_ROOT / 'skills/travel-expense-claim/scripts'))
from source_io import normalize
from workflow import reduce_batches

RUN = IMPLEMENTATION_ROOT / 'artifacts/runs/g2-20261017'
CLOCK = {'date': '2026-11-15', 'timezone': 'Europe/Amsterdam'}
ROLE_FIELDS = {'administration':'Administration reviewer', 'budget_owner':'Budget owner',
               'supervisor':'Supervisor', 'director':'Director'}


def claim(state, identity):
    return next(c for c in state['claims'] if c['claim_id'] == identity)


def original_request(state):
    return next(r for r in state['requests'] if r['request_id'] == 'REQ-C18')


def add_current_c18_approvals(data):
    """Locally constructed current authority isolates the separate Finance hold."""
    trip = next(t for t in data['tables']['Trips'] if t['Trip reference'] == 'T18B')
    for row in list(data['tables']['Review ledger']):
        if row['Subject type'] != 'claim' or row['Subject reference'] != 'C09' or row['Revision'] != '2':
            continue
        old_id = row['Decision reference']
        identity = 'SYN-C18-r2-' + row['Review roles']
        new_row = dict(row, **{'Decision reference':identity, 'Subject reference':'C18',
                              'Reason':'Synthetic authority boundary fixture only', '_locator':identity})
        data['tables']['Review ledger'].append(new_row)
        packet = copy.deepcopy(next(p for p in data['tables']['Review packets'] if p['Decision reference'] == old_id))
        packet.update({k:trip[k] for k in ('Trip reference','Trip revision','Permit reference','Permit revision',
                                         'Business purpose','Client','Schedule coverage','Alternatives considered')})
        packet.update({'Decision reference':identity, 'Expense references':'COST-18B', '_locator':identity})
        data['tables']['Review packets'].append(packet)


class AuthorityBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual = normalize(RUN)
        cls.sealed = json.loads((RUN / 'batches/4.json').read_text())

    def test_actual_c18_keeps_original_request_money_separate_from_replacement(self):
        c, r = claim(self.sealed,'C18'), original_request(self.sealed)
        self.assertEqual((r['trip_id'],r['revision'],r['cost_ids']),('T18',1,['COST-18']))
        self.assertEqual((r['original_amount_cents'],r['amount_cents'],r['net_paid_cents']),(10000,0,10000))
        self.assertEqual((c['trip_id'],c['revision'],c['lines'][0]['cost_id']),('T18B',2,'COST-18B'))
        self.assertEqual((c['payable_cents'],c['unreconciled_paid_cents']),(0,10000))
        self.assertTrue(r['resolution_required'])
        self.assertIsNone(r['resolution_event_id'])
        self.assertFalse(c['closure_candidate'])
        self.assertEqual(c['status'],'held')

    def test_current_approvals_and_matching_total_cannot_reassign_old_transfer(self):
        data=copy.deepcopy(self.actual)
        add_current_c18_approvals(data)
        state=reduce_batches(data,4,CLOCK)[-1]
        c,r=claim(state,'C18'),original_request(state)
        self.assertEqual(c['approval_status'],'approved')
        self.assertEqual(len(c['decision_ids']),3)
        self.assertTrue(all(d.startswith('SYN-C18-r2-') for d in c['decision_ids']))
        # Equality is deliberately present; original request/cost identity still blocks.
        self.assertEqual((c['allowed_cents'],c['paid_cents'],c['balance_cents']),(10000,10000,0))
        self.assertEqual((r['trip_id'],r['cost_ids']),('T18',['COST-18']))
        self.assertEqual((c['status'],c['payable_cents'],c['unreconciled_paid_cents']),('held',0,10000))
        self.assertFalse(c['closure_candidate'])
        self.assertTrue(any('prior_request_basis:REQ-C18' in i for i in c['issue_record_ids']))
        self.assertTrue(any('finance_resolution:REQ-C18' in i for i in c['issue_record_ids']))
        self.assertEqual([r['request_id'] for r in state['requests'] if r['claim_id']=='C18'],['REQ-C18'])

    def test_every_actual_closed_claim_has_exact_source_decisions_and_authorized_actors(self):
        ledger={r['Decision reference']:r for r in self.actual['tables']['Review ledger']}
        packets={p['Decision reference']:p for p in self.actual['tables']['Review packets']}
        people={p['Employee ID']:p for p in self.actual['tables']['People']}
        closed=[c for c in self.sealed['claims'] if c['status']=='closed-reimbursed']
        self.assertTrue(closed)
        for c in closed:
            with self.subTest(claim=c['claim_id']):
                roles=set()
                self.assertTrue(c['decision_ids'])
                for identity in c['decision_ids']:
                    row=ledger[identity]
                    self.assertEqual((row['Subject type'],row['Subject reference'],int(row['Revision']),row['Outcome']),
                                     ('claim',c['claim_id'],c['revision'],'approve'))
                    self.assertEqual(row['_source_id'],'registers')
                    self.assertEqual(packets[identity]['Trip reference'],c['trip_id'])
                    for role in row['Review roles'].splitlines():
                        self.assertEqual(row['Reviewer'],people[c['employee_id']][ROLE_FIELDS[role]])
                        roles.add(role)
                self.assertTrue({'administration','budget_owner','supervisor'} <= roles)
                if c['allowed_cents']>100000:self.assertIn('director',roles)
                self.assertEqual((c['approval_status'],c['balance_cents'],c['issue_record_ids']),('approved',0,[]))

    def test_removing_current_human_approval_blocks_closure_without_erasing_paid_history(self):
        for role in ('administration','budget_owner','supervisor'):
            with self.subTest(role=role):
                data=copy.deepcopy(self.actual)
                data['tables']['Review ledger']=[r for r in data['tables']['Review ledger'] if not
                    (r['Subject reference']=='C19' and r['Revision']=='3' and role in r['Review roles'].splitlines())]
                state=reduce_batches(data,4,CLOCK)[-1]
                c=claim(state,'C19')
                self.assertEqual(c['paid_cents'],8000)
                self.assertNotEqual(c['approval_status'],'approved')
                self.assertEqual(c['status'],'held')
                self.assertFalse(c['closure_candidate'])
                self.assertNotIn('F-C19-4',state['admitted_event_ids'])

    def test_wrong_human_actor_cannot_supply_current_closure_authority(self):
        data=copy.deepcopy(self.actual)
        row=next(r for r in data['tables']['Review ledger'] if r['Subject reference']=='C19' and r['Revision']=='3' and r['Review roles']=='supervisor')
        row['Reviewer']='SYN-NOT-THE-SUPERVISOR'
        state=reduce_batches(data,4,CLOCK)[-1]
        c=claim(state,'C19')
        self.assertEqual((c['status'],c['paid_cents'],c['payable_cents']),('held',8000,0))
        decision=next(d for d in state['decisions'] if d['Decision reference']==row['Decision reference'])
        self.assertFalse(decision['admitted'])
        self.assertIn('wrong actor/role',decision['validation_errors'])
        self.assertFalse(c['closure_candidate'])

    def test_missing_or_wrong_finance_resolution_actor_blocks_zero_balance_closure(self):
        for mode in ('missing','wrong actor'):
            with self.subTest(mode=mode):
                data=copy.deepcopy(self.actual)
                if mode=='missing':
                    data['tables']['Finance activity']=[e for e in data['tables']['Finance activity'] if e['Activity reference']!='F-C20-3']
                else:
                    next(e for e in data['tables']['Finance activity'] if e['Activity reference']=='F-C20-3')['Finance officer']='SYN-UNAUTHORIZED'
                state=reduce_batches(data,4,CLOCK)[-1]
                c=claim(state,'C20')
                self.assertEqual((c['approval_status'],c['paid_cents'],c['balance_cents']),('approved',10000,0))
                self.assertEqual(c['status'],'held')
                self.assertFalse(c['closure_candidate'])
                self.assertNotIn('F-C20-3',state['admitted_event_ids'])


if __name__=='__main__':
    unittest.main()

"""Deterministic G1 reducer: complete original batches 1–2, no side effects.

Policy POL-2026.2 plus interview D-4 arrival semantics. Later revisions,
refund/retry resolution and replay are deliberately reserved for G2.
"""
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from source_io import SourceError

ROLES = {'administration': 'Administration reviewer', 'budget_owner': 'Budget owner',
         'supervisor': 'Supervisor', 'director': 'Director'}


def cents(value, exact=False):
    n = Decimal(value) * 100
    if not n.is_finite() or n < 0 or (exact and n != n.to_integral_value()):
        raise SourceError('Invalid nonnegative integer-cent money: ' + str(value))
    return int(n.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def timestamp(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.utcoffset() is None:
        raise SourceError('Event timestamp has no timezone')
    return t


def filing_deadline(end):
    d = date.fromisoformat(end)
    month = d.month + 2
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def refs(record):
    return {'source_id': record['_source_id'], 'locator': record['_locator']}


def repair_action(claim, line, fact, trip):
    identity = f"{claim['claim_id']} r{claim['revision']}, {line['cost_id']}, {claim['employee_id']}, {claim['trip_id']} r{claim['trip_revision']}"
    actions = {
        'merchant_payment_missing_or_ambiguous': f"Provide one settled merchant transaction matching {identity}, receipt {line['receipt_id']}, {line['original_amount']} {line['currency']}, and its paid date; a receipt alone is insufficient.",
        'receipt_missing_or_mismatch': f"Provide receipt {line['receipt_id']} matching {identity}, currency {line['currency']} and gross {line['original_amount']}.",
        'fx_missing_or_ambiguous': f"Finance must supply the exact employee-payment-date EUR-per-{line['currency']} rate for {identity}; retain its effective date and reference.",
        'cap_missing_or_ambiguous': f"Finance must supply the category cap in {line['currency']} applicable in {trip['Destination']} on the employee-payment date for {identity}; include units and effective dates.",
        'filed_before_employee_payment': f"Clarify first filing {line['first_submitted']} for {identity} against the later settled merchant paid date; provide corrected source evidence without silently changing the original filing.",
        'late_filing': f"Obtain a Finance exception explicitly covering late_filing for {identity}, with allowed original amount and reason; otherwise retain the hold.",
        'late_permit': f"Obtain a Finance exception explicitly covering late_permit for {identity}; preserve the original arrangement-authority breach and obtain current claim reviews.",
        'permit_unapproved': f"Supply valid permit authority for {identity}, or a Finance exception explicitly covering permit_unapproved for reimbursement only; do not retroactively approve arrangements.",
        'permit_payment_order_unknown': f"Supervisor/Finance must establish the order of permission and the same-day commitment/payment for {identity}; date-only evidence cannot establish earlier permission.",
        'category_unknown': f"Administration/Finance must classify the actual purchase for {identity} using authoritative category evidence; do not assume zero entitlement.",
    }
    return actions.get(fact, f"Resolve {fact} for {identity} with specific authorized evidence, then revalidate affected review/payment work.")


def unique(rows, key):
    result = {}
    for r in rows:
        identity = key(r)
        if identity in result:
            raise SourceError('Duplicate source identity: ' + str(identity))
        result[identity] = r
    return result


def approval_order(previous, current):
    """I4 accepts simultaneous arrival only in the same arrival batch."""
    a, b = timestamp(previous['Decision time (UTC)']), timestamp(current['Decision time (UTC)'])
    return b > a or (b == a and previous['Arrival batch'] == current['Arrival batch'])


def review(kind, subject, revision, trip, person, amount, costs, tables, batch, case_date):
    rows = [r for r in tables['Review ledger'] if int(r['Arrival batch']) <= batch
            and r['Subject type'] == kind and r['Subject reference'] == subject
            and int(r['Revision']) == revision]
    packets = unique(tables['Review packets'], lambda p: p['Decision reference'])
    required = ['administration', 'budget_owner', 'supervisor']
    if amount is not None and amount > 100000:
        required.append('director')
    by_role, records, problems = {}, [], []
    for r in rows:
        errors = []
        roles = r['Review roles'].splitlines()
        p = packets.get(r['Decision reference'])
        if not roles or any(role not in ROLES or r['Reviewer'] != person[ROLES[role]] for role in roles):
            errors.append('wrong actor/role')
        if len(roles) > 1 and (set(roles) != {'budget_owner', 'supervisor'} or person['Budget owner'] != person['Supervisor']):
            errors.append('unauthorized combined roles')
        if len(set(roles)) != len(roles):
            errors.append('duplicate role')
        if set(r['Source revisions'].splitlines()) != {'DW-D-2', 'POL-2026.2', 'SRC-D-3'}:
            errors.append('source version conflict')
        if timestamp(r['Decision time (UTC)']).astimezone(ZoneInfo('Europe/Amsterdam')).date() > case_date:
            errors.append('future decision')
        if r['Outcome'] not in ('approve', 'return', 'reject') or not r['Reason']:
            errors.append('invalid outcome/reason')
        if r['Outcome'] == 'return' and not r['Repair requested']:
            errors.append('return missing repair')
        if not p:
            errors.append('missing packet')
        else:
            expected = {'Employee ID': person['Employee ID'], 'Trip reference': trip['Trip reference'],
                        'Trip revision': trip['Trip revision'], 'Permit reference': trip['Permit reference'],
                        'Permit revision': trip['Permit revision'], 'Policy revision': 'POL-2026.2'}
            for key in ('Business purpose', 'Client', 'Schedule coverage', 'Alternatives considered'):
                expected[key] = trip[key]
            if any(p[k] != v for k, v in expected.items()):
                errors.append('packet subject/trip/policy/context mismatch')
            if kind == 'claim' and set(p['Expense references'].splitlines()) != set(costs):
                errors.append('packet cost mismatch')
            if kind == 'permit' and (not p['Reviewed estimate (EUR)'] or cents(p['Reviewed estimate (EUR)']) != amount):
                errors.append('permit estimate mismatch')
            budget_ids = {b['Ledger reference'] for b in tables['Budget'] if all(b[k] == person[k] for k in ('Department', 'Project', 'Budget period'))}
            if set(p['Budget record references'].splitlines()) != budget_ids:
                errors.append('incomplete budget packet')
            if 'director' in roles and p['Budget owner position'] != 'Approved':
                errors.append('director packet missing budget position')
            if p['Travel cancellation references']:
                errors.append('cancellation-aware review deferred to G2')
        record = dict(r, packet=p, validation_errors=errors, admitted=not errors)
        records.append(record)
        if errors:
            problems.append(r['Decision reference'] + ': ' + ', '.join(errors))
            continue
        for role in roles:
            if role in by_role:
                problems.append('conflicting repeated role: ' + role)
            by_role[role] = r
    previous = None
    outcome = 'approved'
    for role in required:
        r = by_role.get(role)
        if not r:
            problems.append('missing ' + role + ' response')
            outcome = 'pending'
            break
        if previous and not approval_order(previous, r):
            problems.append('dependent review arrival out of sequence: ' + role)
            outcome = 'held'
            break
        if r['Outcome'] != 'approve':
            outcome = r['Outcome']
            break
        previous = r
    if problems and outcome == 'approved':
        outcome = 'held'
    return dict(outcome=outcome, decision_ids=[r['Decision reference'] for r in records if r['admitted']],
                records=records, problems=problems,
                approved_at=max((r['Decision time (UTC)'] for r in by_role.values()), default=None))


def line_review(claim, line, trip, person, receipts, tables, permit):
    finding = dict(cost_id=line['cost_id'], source_ids=[claim['_source_id'], 'receipts', 'registers'],
                   status='unresolved', allowed_cents=None, reason='', evidence=[refs(claim)], findings=[])
    errors, eligibility = [], []
    receipt = receipts.get(line['receipt_id'])
    if not receipt or any(receipt[k] != v for k, v in {'cost_id': line['cost_id'], 'employee_id': claim['employee_id'], 'trip_id': claim['trip_id'], 'currency': line['currency']}.items()) or Decimal(receipt['gross']) != Decimal(line['original_amount']):
        errors.append('receipt_missing_or_mismatch')
    else:
        finding['evidence'].append(refs(receipt))
    merchant = [m for m in tables['Merchant payments'] if m['Expense reference'] == line['cost_id']
                and m['Employee ID'] == claim['employee_id'] and m['Trip reference'] == claim['trip_id']
                and m['Currency'] == line['currency'] and Decimal(m['Gross amount']) == Decimal(line['original_amount'])
                and m['Receipt reference'] == line['receipt_id'] and m['Payment status'] == 'settled']
    if len(merchant) != 1:
        errors.append('merchant_payment_missing_or_ambiguous')
    if errors:
        finding.update(reason='; '.join(errors), findings=errors)
        return finding
    m = merchant[0]
    finding['evidence'].append(refs(m))
    paid = date.fromisoformat(m['Paid date'])
    first = date.fromisoformat(line['first_submitted'])
    if first < paid:
        eligibility.append('filed_before_employee_payment')
    if first > filing_deadline(trip['End date']):
        eligibility.append('late_filing')
    if trip['International'] == 'True':
        if permit['outcome'] != 'approved':
            eligibility.append('permit_unapproved')
        else:
            approved = timestamp(permit['approved_at']).astimezone(ZoneInfo('Europe/Amsterdam')).date()
            commitment = date.fromisoformat(trip['First commitment date']) if trip['First commitment date'] else paid
            if approved >= min(commitment, paid):
                eligibility.append('late_permit' if approved > min(commitment, paid) else 'permit_payment_order_unknown')
    gross = Decimal(receipt['gross'])
    category = receipt['category']
    if category == 'personal':
        gross = Decimal(0)
    elif category in ('lodging', 'meals'):
        caps = [c for c in tables['Caps'] if c['Destination'] == trip['Destination'] and c['Category'] == category
                and c['Currency'] == line['currency'] and c['Effective from'] <= m['Paid date'] <= c['Effective to']]
        if len(caps) != 1:
            errors.append('cap_missing_or_ambiguous')
        else:
            gross = min(gross, Decimal(caps[0]['Amount per unit']) * receipt['units'])
            finding['evidence'].append(refs(caps[0]))
    elif category not in ('transport', 'conference'):
        errors.append('category_unknown')
    rates = [r for r in tables['FX'] if r['Currency'] == line['currency'] and r['Rate date'] == m['Paid date']]
    rate = Decimal(1) if line['currency'] == 'EUR' else None
    if line['currency'] != 'EUR':
        if len(rates) != 1:
            errors.append('fx_missing_or_ambiguous')
        else:
            rate = Decimal(rates[0]['EUR per currency unit'])
            finding['evidence'].append(refs(rates[0]))
    if claim.get('exception'):
        errors.append('scoped_exception_processing_deferred_to_G2')
    arithmetic = cents(gross * rate) if rate is not None and not errors else None
    finding.update(arithmetic_cents=arithmetic, findings=errors + eligibility)
    if errors or eligibility:
        finding['reason'] = '; '.join(errors + eligibility)
    else:
        finding.update(status='excluded' if category == 'personal' else 'supported', allowed_cents=arithmetic,
                       reason='Personal cost has zero entitlement' if category == 'personal' else 'Receipt and settled merchant proof matched; policy arithmetic supported')
    return finding


def reduce_batch(data, batch, case_clock):
    if batch not in (1, 2):
        raise SourceError('G1 supports only original batches 1 and 2; G2 not implemented')
    if case_clock != {'date': '2026-11-15', 'timezone': 'Europe/Amsterdam'}:
        raise SourceError('Case clock differs from implemented source policy')
    case_date = date.fromisoformat(case_clock['date'])
    tables = data['tables']
    # Missing history is unknown, never zero. Source parser also checks all native tabs.
    if not tables.get('Finance activity'):
        raise SourceError('Unknown paid history cannot fit paid_cents; cannot seal; Finance must restore complete history')
    people = unique(tables['People'], lambda r: r['Employee ID'])
    trips = unique(tables['Trips'], lambda r: (r['Trip reference'], int(r['Trip revision'])))
    receipts = unique(data['receipts'], lambda r: r['receipt_id'])
    current = {}
    for c in data['claims']:
        if int(c['batch_id']) <= batch:
            if c['claim_id'] in current:
                raise SourceError('Claim corrections are a G2 branch; refusing to erase history')
            current[c['claim_id']] = c
    issues, decisions, permits, claims, requests = [], [], [], [], []

    def issue(subject, revision, fact, reason, owner, action, evidence=()):
        record = dict(record_id=f'{subject}:r{revision}:{fact}', subject_id=subject, revision=revision,
                      fact=fact, reason=reason, owner=owner, resolution_needed=action,
                      source_refs=list(evidence), status='open', run_batch=str(batch))
        if not any(i['record_id'] == record['record_id'] for i in issues):
            issues.append(record)
        return record['record_id']

    # Retain all independent travel bases, even when no claim exists.
    permit_map = {}
    for key, trip in trips.items():
        person = people[trip['Employee ID']]
        if trip['International'] == 'True':
            result = review('permit', trip['Permit reference'], int(trip['Permit revision']), trip, person,
                            cents(trip['Estimate (EUR)']), [], tables, batch, case_date)
            permit_map[key] = result
            decisions.extend(result['records'])
            permits.append(dict(permit_id=trip['Permit reference'], revision=int(trip['Permit revision']),
                                trip_id=key[0], trip_revision=key[1], estimate_cents=cents(trip['Estimate (EUR)']),
                                status=result['outcome'], decision_ids=result['decision_ids'], evidence=[refs(trip)]))
    for cid, c in sorted(current.items()):
        trip = trips.get((c['trip_id'], c['trip_revision']))
        if not trip or trip['Employee ID'] != c['employee_id']:
            raise SourceError(f'{cid}: missing or mismatched trip identity; Administration must repair')
        person = people[c['employee_id']]
        lines = [line_review(c, line, trip, person, receipts, tables, permit_map.get((c['trip_id'], c['trip_revision']))) for line in c['lines']]
        allowed = sum(l['allowed_cents'] for l in lines) if all(l['allowed_cents'] is not None for l in lines) else None
        rev = review('claim', cid, c['revision'], trip, person, allowed, [l['cost_id'] for l in lines], tables, batch, case_date)
        decisions.extend(rev['records'])
        record = dict(claim_id=cid, revision=c['revision'], trip_id=c['trip_id'], trip_revision=c['trip_revision'],
                      employee_id=c['employee_id'], status='pending', lines=lines, allowed_cents=allowed, paid_cents=0,
                      balance_cents=None, decision_ids=rev['decision_ids'], next_owner=None, reason='Awaiting review',
                      approval_status=rev['outcome'], approval_at=rev['approved_at'], source_refs=[refs(c)],
                      closure_candidate=False, issue_record_ids=[])
        for l in lines:
            for fact in l['findings']:
                owner = 'Finance' if any(s in fact for s in ('fx_', 'cap_', 'late_', 'permit_', 'category_')) else c['employee_id'] + ' / Administration'
                issue(cid, c['revision'], l['cost_id'] + ':' + fact, f"{l['cost_id']}: {fact}", owner,
                      repair_action(c, next(x for x in c['lines'] if x['cost_id'] == l['cost_id']), fact, trip), l['evidence'])
        if c['status'] == 'withdrawn' or rev['outcome'] == 'reject':
            record.update(status='withdrawn' if c['status'] == 'withdrawn' else 'rejected', allowed_cents=0,
                          balance_cents=0, reason=c['reason'] if c['status'] == 'withdrawn' else 'Authorized reviewer rejected: ' + next(r['Reason'] for r in rev['records'] if r['Outcome'] == 'reject'))
        elif rev['outcome'] == 'return':
            r = next(r for r in rev['records'] if r['Outcome'] == 'return')
            issue(cid, c['revision'], 'review_return', r['Reason'], c['employee_id'] + ' / ' + r['Reviewer'], r['Repair requested'], [refs(r)])
        elif allowed is not None and allowed > 0 and rev['outcome'] != 'approved':
            issue(cid, c['revision'], 'review_authority', '; '.join(rev['problems']) or 'Required review not approved',
                  'Administration / authorized reviewers', 'Obtain valid current subject/revision responses; do not infer approval.', [refs(c)])
        claims.append(record)
    by_claim = {c['claim_id']: c for c in claims}
    events, admitted, seen = [], [], {}
    finance = [r for r in tables['Finance activity'] if int(r['Arrival batch']) <= batch]
    finance.sort(key=lambda r: (int(r['Arrival batch']), timestamp(r['Activity time (UTC)']), r['Activity reference']))
    for e in finance:
        eid, cid, rid, kind = e['Activity reference'], e['Claim reference'], e['Request reference'], e['Activity type']
        payload = {k: v for k, v in e.items() if k not in ('Arrival batch', '_source_id', '_locator')}
        if eid in seen:
            if seen[eid] != payload:
                issue(cid, by_claim[cid]['revision'] if cid in by_claim else 1, eid, 'Conflicting Finance event payload', 'Finance', 'Resolve immutable event conflict; admitted history retained.', [refs(e)])
            continue
        seen[eid] = payload
        c = by_claim.get(cid)
        error = None
        request = next((r for r in requests if r['request_id'] == rid), None)
        if not c:
            error = 'Unknown claim/request'
        else:
            person = people[c['employee_id']]
            if e['Finance officer'] != person['Finance officer'] or e['Payee ID'] != person['Payee ID'] or e['Currency'] != 'EUR':
                error = 'Wrong Finance actor/payee/currency'
            elif timestamp(e['Activity time (UTC)']).astimezone(ZoneInfo('Europe/Amsterdam')).date() > case_date:
                error = 'Future Finance event'
            elif kind == 'accepted':
                amount = cents(e['Obligation (EUR)'], exact=True)
                if request or amount <= 0 or c['allowed_cents'] != amount or c['approval_status'] != 'approved' or timestamp(e['Activity time (UTC)']) < timestamp(c['approval_at']):
                    error = 'Acceptance cannot bind current authorized obligation'
                else:
                    request = dict(request_id=rid, claim_id=cid, revision=c['revision'], amount_cents=amount,
                                   payee=person['Payee ID'], currency='EUR', status='accepted', decision_ids=c['decision_ids'],
                                   accepted_at=e['Activity time (UTC)'], event_ids=[], cost_ids=[l['cost_id'] for l in c['lines']], source_refs=[refs(e)])
                    requests.append(request)
            elif not request or request['claim_id'] != cid or timestamp(e['Activity time (UTC)']) < timestamp(request['accepted_at']):
                error = 'Unmatched request or event predates acceptance'
            elif kind == 'settled':
                amount = cents(e['Amount (EUR)'], exact=True)
                if amount <= 0 or request['status'] == 'held':
                    error = 'Invalid transfer amount or missing retry authorization'
                else:
                    c['paid_cents'] += amount
                    request['status'] = 'settled' if c['paid_cents'] >= request['amount_cents'] else 'dispatched'
            elif kind == 'failed':
                request['status'] = 'held'
                issue(cid, c['revision'], 'finance_retry', 'Finance attempt failed; no transfer effect', 'Finance', 'Supply explicit retry authorization before a new attempt.', [refs(e)])
            elif kind == 'cancellation_requested':
                request['status'] = 'cancel-pending'
                issue(cid, c['revision'], 'finance_cancel', 'Finance cancellation requested, not confirmed', 'Finance', 'Confirm original request status/cancellation; hold competing replacements.', [refs(e)])
            else:
                error = 'Finance branch not implemented in G1: ' + kind
        if error:
            issue(cid, c['revision'] if c else 1, eid, error, 'Finance', 'Supply matching authorized evidence or complete G2 branch; do not invent money.', [refs(e)])
        else:
            admitted.append(eid)
            request['event_ids'].append(eid)
        events.append(dict(e, admitted=error is None, validation_error=error))

    cancellations, cancellation_events = [], []
    deliveries = [r for r in tables['Travel cancellations'] if int(r['Arrival batch']) <= batch]
    deliveries.sort(key=lambda r: (int(r['Arrival batch']), timestamp(r['Activity time (UTC)']), r['Cancellation activity reference']))
    seen_c = {}
    for e in deliveries:
        eid, cid = e['Cancellation activity reference'], e['Cancellation reference']
        payload = {k: v for k, v in e.items() if k not in ('Arrival batch', '_source_id', '_locator')}
        if eid in seen_c and seen_c[eid] == payload:
            continue
        key = (e['Trip reference'], int(e['Trip revision']))
        trip = trips.get(key)
        state = next((c for c in cancellations if c['cancellation_id'] == cid), None)
        error = None
        if eid in seen_c:
            error = 'Conflicting cancellation payload'
        elif not trip or e['Permit reference'] != trip['Permit reference'] or e['Permit revision'] != trip['Permit revision'] or e['Cancelled subject'] not in ('trip', 'permit') or (e['Cancelled subject'] == 'permit' and not e['Permit reference']):
            error = 'Mismatched cancellation target'
        elif timestamp(e['Activity time (UTC)']).astimezone(ZoneInfo('Europe/Amsterdam')).date() > case_date:
            error = 'Future cancellation'
        elif e['Action'] == 'requested':
            if state or e['Acting employee or supervisor'] != trip['Employee ID'] or e['Initiation activity reference'] or e['Effective time (UTC)']:
                error = 'Invalid cancellation initiation'
            else:
                affected = [c['claim_id'] for c in claims if (c['trip_id'], c['trip_revision']) == key]
                state = dict(cancellation_id=cid, target_type=e['Cancelled subject'], trip_id=key[0], trip_revision=key[1],
                             permit_id=e['Permit reference'] or None, permit_revision=int(e['Permit revision']) if e['Permit revision'] else None,
                             status='requested', admitted_cancellation_event_ids=[eid], requested_at=e['Activity time (UTC)'], confirmed_at=None,
                             effective_at=None, affected_claim_ids=affected, original_request_ids=[r['request_id'] for r in requests if r['claim_id'] in affected],
                             financial_status='unresolved' if affected or trip['First commitment date'] else 'no-financial-effect',
                             next_owner=people[trip['Employee ID']]['Supervisor'], reason=e['Business reason'], issue_record_ids=[])
                cancellations.append(state)
        elif e['Action'] == 'confirmed':
            if not state or state['status'] == 'confirmed' or e['Initiation activity reference'] != state['admitted_cancellation_event_ids'][0] or key != (state['trip_id'], state['trip_revision']) or e['Cancelled subject'] != state['target_type'] or e['Acting employee or supervisor'] != people[trip['Employee ID']]['Supervisor'] or timestamp(e['Activity time (UTC)']) <= timestamp(state['requested_at']) or e['Effective time (UTC)'] != e['Activity time (UTC)']:
                error = 'Invalid confirmation: exact initiation/target/actor and strictly later occurrence required'
            else:
                state.update(status='confirmed', confirmed_at=e['Activity time (UTC)'], effective_at=e['Effective time (UTC)'],
                             next_owner='Finance / Administration' if state['financial_status'] == 'unresolved' else None, reason=e['Business reason'])
                state['admitted_cancellation_event_ids'].append(eid)
        else:
            error = 'Unknown cancellation action'
        seen_c[eid] = payload
        if error:
            iid = issue(cid, key[1], eid, error, 'Administration / Supervisor', 'Supply a valid matching initiation/confirmation; retained history remains.', [refs(e)])
            if state:
                state['issue_record_ids'].append(iid)
        cancellation_events.append(dict(e, admitted=error is None, validation_error=error))
    for c in cancellations:
        if c['financial_status'] == 'unresolved':
            iid = issue(c['cancellation_id'], c['trip_revision'], 'financial_disposition', 'Travel cancellation has costs or obligations; it does not release money', 'Finance / Administration', 'Supply scoped cost disposition, current cancellation-aware reviews and any required original-request resolution (G2).')
            c['issue_record_ids'].append(iid)
        for cid in c['affected_claim_ids']:
            claim = by_claim[cid]
            issue(cid, claim['revision'], 'travel_cancellation:' + c['cancellation_id'], 'Cancellation ' + c['status'] + '; original purchase evidence retained',
                  c['next_owner'] or 'Finance / Administration', 'Resolve cancellation-dependent eligibility/review; keep original Finance obligation and payment history.')
            if c['status'] == 'confirmed':
                claim['pre_cancellation_allowed_cents'] = claim['allowed_cents']
                claim['allowed_cents'] = None
    for c in claims:
        own = [i for i in issues if i['subject_id'] == c['claim_id']]
        if c['allowed_cents'] is not None and (c['approval_status'] == 'approved' or c['allowed_cents'] == 0):
            c['balance_cents'] = c['allowed_cents'] - c['paid_cents']
        if c['balance_cents'] is not None and c['balance_cents'] < 0:
            issue(c['claim_id'], c['revision'], 'overpayment', 'Confirmed transfers exceed the current reviewed obligation', 'Finance', 'Reconcile linked confirmed refund and explicit resolution; matching a later total alone is insufficient.')
        own = [i for i in issues if i['subject_id'] == c['claim_id']]
        if own:
            c.update(status='held', next_owner=own[0]['owner'], reason='; '.join(i['reason'] for i in own), issue_record_ids=[i['record_id'] for i in own])
        elif c['status'] in ('withdrawn', 'rejected'):
            if c['paid_cents']:
                c.update(status='held', next_owner='Finance', reason='Withdrawal/rejection has financial effect; resolution required')
        elif c['allowed_cents'] == 0:
            c.update(status='closed-no-payment', next_owner=None, reason='Known zero entitlement; no financial effect')
        elif c['approval_status'] == 'approved':
            c['status'] = 'closed-reimbursed' if c['balance_cents'] == 0 else ('ready' if c['paid_cents'] == 0 else 'pending')
            c['closure_candidate'] = c['balance_cents'] == 0
            c['next_owner'] = None if c['closure_candidate'] else 'Finance'
            c['reason'] = 'Current approvals, supported entitlement and confirmed payment agree; no outstanding issue or Finance balance' if c['closure_candidate'] else 'Current approvals valid; await confirmed Finance settlement'
        c['supported_cents'] = sum(l['allowed_cents'] or 0 for l in c['lines'] if l['status'] == 'supported')
        c['payable_cents'] = max(0, c['balance_cents'] or 0) if not own and c['approval_status'] == 'approved' else 0
        accepted_remaining = sum(max(0, r['amount_cents'] - c['paid_cents']) for r in requests if r['claim_id'] == c['claim_id'])
        c['held_cents'] = max(accepted_remaining, max(0, c['balance_cents'] or 0)) if own else 0
        c['held_amount_unknown'] = bool(own and c['allowed_cents'] is None)
    travel_bases = []
    for key, trip in trips.items():
        affected = [c for c in cancellations if (c['trip_id'], c['trip_revision']) == key]
        trip_state = 'active'
        permission = permit_map[key]['outcome'] if key in permit_map else 'not-required'
        for c in affected:
            if c['status'] == 'requested':
                trip_state = 'arrangements-paused'
                permission = 'paused'
            else:
                if c['target_type'] == 'trip':
                    trip_state = 'retired'
                permission = 'retired' if trip['Permit reference'] else 'not-required'
        travel_bases.append(dict(trip_id=key[0], trip_revision=key[1], status=trip_state,
                                 permission=permission, cancellation_ids=[c['cancellation_id'] for c in affected], source_refs=[refs(trip)]))
        for p in permits:
            if (p['trip_id'], p['trip_revision']) == key:
                p['current_permission'] = permission
    budget = []
    groups = sorted({tuple(p[k] for k in ('Department', 'Project', 'Budget period')) for p in people.values()})
    for group in groups:
        base = [r for r in tables['Budget'] if tuple(r[k] for k in ('Department', 'Project', 'Budget period')) == group]
        alloc = sum(cents(r['Allocation or commitment (EUR)']) for r in base if r['Entry type'] == 'allocation')
        old_net = sum(cents(r['Settled (EUR)']) - cents(r['Refunded (EUR)']) for r in base if r['Entry type'] == 'obligation')
        old_remaining = sum(max(0, cents(r['Allocation or commitment (EUR)']) - (cents(r['Settled (EUR)']) - cents(r['Refunded (EUR)']))) for r in base if r['Entry type'] == 'obligation')
        group_requests = [r for r in requests if tuple(people[by_claim[r['claim_id']]['employee_id']][k] for k in ('Department', 'Project', 'Budget period')) == group]
        new_net = sum(by_claim[r['claim_id']]['paid_cents'] for r in group_requests)
        new_remaining = sum(max(0, r['amount_cents'] - by_claim[r['claim_id']]['paid_cents']) for r in group_requests)
        budget.append(dict(department=group[0], project=group[1], period=group[2], allocation_cents=alloc, net_settled_cents=old_net+new_net,
                           remaining_commitments_cents=old_remaining+new_remaining, available_cents=alloc-old_net-new_net-old_remaining-new_remaining,
                           source_refs=[refs(r) for r in base], accepted_request_ids=[r['request_id'] for r in group_requests]))
    return dict(presentation_version=2, claims=claims, requests=requests, travel_cancellations=cancellations, admitted_event_ids=admitted,
                issues=issues, decisions=decisions, permits=permits, trips=tables['Trips'], finance_events=events,
                cancellation_events=cancellation_events, travel_bases=travel_bases, budget=budget,
                coverage={'through_batch': batch, 'delivered_claims': len(current), 'review_deliveries': sum(int(r['Arrival batch']) <= batch for r in tables['Review ledger']),
                          'finance_deliveries': len(finance), 'cancellation_deliveries': len(deliveries), 'deferred_batches': [3, 4],
                          'status': 'partial-G1', 'limits': ['G2 corrections/partial-response history, remaining cancellations/Finance branches and replay/recovery not implemented']})

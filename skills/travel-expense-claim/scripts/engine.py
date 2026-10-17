"""Deterministic source-policy helpers for complete batch reduction; no side effects.

Policy POL-2026.2 plus interview D-4 arrival semantics.
Workflow state and financial-event history are implemented in workflow.py.
"""
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from zoneinfo import ZoneInfo

from source_io import SourceError

ROLES = {'administration': 'Administration reviewer', 'budget_owner': 'Budget owner',
         'supervisor': 'Supervisor', 'director': 'Director'}


def cents(value, exact=False):
    try:
        n = Decimal(value) * 100
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SourceError('Unknown/invalid money; Finance must restore monetary evidence before sealing paid_cents') from exc
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
        'travel_cancellation': f"Finance must explicitly determine reimbursement eligibility for {identity}, naming every applicable confirmed cancellation ID in a scoped exception; then obtain current reviews acknowledging those cancellations and reconcile the original Finance request.",
        'prior_cost_obligation': f"Finance must reconcile the existing request containing {line['cost_id']} with {identity}; supply the related claim/request linkage and disposition before any second reimbursement.",
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


def review(kind, subject, revision, trip, person, amount, costs, tables, batch, case_date, cancellations=()):
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
            expected_cancel = {c['cancellation_id'] for c in cancellations if c['status'] == 'confirmed'}
            if set(p['Travel cancellation references'].splitlines()) != expected_cancel:
                errors.append('packet cancellation context mismatch')
            if any(timestamp(r['Decision time (UTC)']) <= timestamp(c['confirmed_at']) for c in cancellations if c['status'] == 'confirmed'):
                errors.append('review reply predates cancellation context')
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


def line_review(claim, line, trip, person, receipts, tables, permit, cancellations=()):
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
    confirmed = [c for c in cancellations if c['status'] == 'confirmed']
    if confirmed:
        eligibility.append('travel_cancellation')
        if any(c['effective_at'][:10] == m['Paid date'] for c in confirmed):
            eligibility.append('cancellation_payment_order_unknown')
    original_findings = errors + eligibility
    original_gross = gross
    exception = claim.get('exception')
    if exception and exception.get('cost_id') == line['cost_id']:
        coverage = {value.strip().lower().replace(' ', '_') for value in exception['covered_issues']}
        valid = (exception['actor'] == person['Finance officer'] and exception['claim_id'] == claim['claim_id']
                 and exception['revision'] == claim['revision'] and exception.get('reason')
                 and coverage <= {'late_filing', 'late_permit', 'permit_unapproved', 'travel_cancellation'})
        if 'travel_cancellation' in coverage:
            valid = valid and len(confirmed) == 1 and exception.get('cancellation_id') == confirmed[0]['cancellation_id']
        if valid:
            replacement = Decimal(exception['allowed_original_amount'])
            if not replacement.is_finite() or replacement < 0:
                valid = False
        if valid:
            gross = replacement
            eligibility = [f for f in eligibility if f not in coverage]
            finding['exception'] = dict(exception, source_ref=refs(claim))
            finding['resolved_findings'] = [f for f in original_findings if f in coverage]
        else:
            errors.append('invalid_scoped_exception')
    arithmetic = cents(gross * rate) if rate is not None and not errors else None
    finding.update(arithmetic_cents=arithmetic, original_arithmetic_cents=cents(original_gross * rate) if rate is not None and not errors else None,
                   original_findings=original_findings, findings=errors + eligibility, merchant_paid_date=m['Paid date'])
    if errors or eligibility:
        finding['reason'] = '; '.join(errors + eligibility)
    else:
        finding.update(status='excluded' if category == 'personal' else 'supported', allowed_cents=arithmetic,
                       reason='Personal cost has zero entitlement' if category == 'personal' else 'Receipt and settled merchant proof matched; policy arithmetic supported')
    return finding


def reduce_batch(data, batch, case_clock):
    from workflow import reduce_batches
    return reduce_batches(data, batch, case_clock)[-1]

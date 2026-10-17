"""Arrival-batch state, revision history and Finance reconciliation.

Only source facts change business authority or money. Recomputing from the
complete retained delivery log is deterministic and has no external effects.
"""
from copy import deepcopy
from datetime import date
from zoneinfo import ZoneInfo

from engine import cents, filing_deadline, line_review, refs, repair_action, review, timestamp, unique
from source_io import SourceError


def payload(record, excluded=()):
    return {k: v for k, v in record.items() if k not in ('Arrival batch', '_source_id', '_locator', *excluded)}


def cancellation_view(data, batch, history, requests, people, trips, issue, case_date):
    deliveries = [e for e in data['tables']['Travel cancellations'] if int(e['Arrival batch']) <= batch]
    unique_events, conflicts, observations = {}, set(), []
    for e in sorted(deliveries, key=lambda r: (int(r['Arrival batch']), r['_locator'])):
        eid = e['Cancellation activity reference']
        if eid in unique_events:
            if payload(e) != payload(unique_events[eid]):
                conflicts.add(eid)
        else:
            unique_events[eid] = e
    states, admitted, errors = {}, set(), {}
    # Establish exact valid initiations before resolving confirmations. This
    # rechecks an early orphan when its initiation arrives in a later batch.
    for action in ('requested', 'confirmed'):
        rows = [e for e in unique_events.values() if e['Action'] == action]
        rows.sort(key=lambda e: (int(e['Arrival batch']), timestamp(e['Activity time (UTC)']), e['Cancellation activity reference']))
        for e in rows:
            eid, cid = e['Cancellation activity reference'], e['Cancellation reference']
            key = (e['Trip reference'], int(e['Trip revision']))
            trip = trips.get(key)
            state = states.get(cid)
            error = None
            if not trip or e['Permit reference'] != trip['Permit reference'] or e['Permit revision'] != trip['Permit revision'] or e['Cancelled subject'] not in ('trip', 'permit') or (e['Cancelled subject'] == 'permit' and not e['Permit reference']):
                error = 'Mismatched or stale cancellation target'
            elif timestamp(e['Activity time (UTC)']).astimezone(ZoneInfo('Europe/Amsterdam')).date() > case_date:
                error = 'Future cancellation observation'
            elif action == 'requested':
                if state or e['Acting employee or supervisor'] != trip['Employee ID'] or e['Initiation activity reference'] or e['Effective time (UTC)']:
                    error = 'Invalid or repeated cancellation initiation'
                else:
                    affected = sorted({c['claim_id'] for c in history if (c['trip_id'], c['trip_revision']) == key})
                    original = [r['request_id'] for r in requests.values() if (r['trip_id'], r['trip_revision']) == key]
                    has_cost = any(m['Trip reference'] == key[0] for m in data['tables']['Merchant payments'])
                    state = dict(cancellation_id=cid, target_type=e['Cancelled subject'], trip_id=key[0], trip_revision=key[1],
                                 permit_id=e['Permit reference'] or None, permit_revision=int(e['Permit revision']) if e['Permit revision'] else None,
                                 status='requested', admitted_cancellation_event_ids=[eid], requested_at=e['Activity time (UTC)'],
                                 confirmed_at=None, effective_at=None, affected_claim_ids=affected, original_request_ids=original,
                                 financial_status='unresolved' if affected or original or has_cost or trip['First commitment date'] else 'no-financial-effect',
                                 next_owner=people[trip['Employee ID']]['Supervisor'], reason=e['Business reason'], issue_record_ids=[], source_refs=[refs(e)])
                    states[cid] = state
            else:
                if not state or state['status'] == 'confirmed' or e['Initiation activity reference'] != state['admitted_cancellation_event_ids'][0] or key != (state['trip_id'], state['trip_revision']) or e['Cancelled subject'] != state['target_type'] or e['Acting employee or supervisor'] != people[trip['Employee ID']]['Supervisor'] or timestamp(e['Activity time (UTC)']) <= timestamp(state['requested_at']) or e['Effective time (UTC)'] != e['Activity time (UTC)']:
                    error = 'Invalid confirmation: exact initiation/target/actor and strictly later occurrence required'
                else:
                    state.update(status='confirmed', confirmed_at=e['Activity time (UTC)'], effective_at=e['Effective time (UTC)'],
                                 next_owner='Finance / Administration' if state['financial_status'] == 'unresolved' else None, reason=e['Business reason'])
                    state['admitted_cancellation_event_ids'].append(eid)
                    state['source_refs'].append(refs(e))
            if error:
                errors[eid] = error
            else:
                admitted.add(eid)
    for eid, e in unique_events.items():
        if e['Action'] not in ('requested', 'confirmed'):
            errors[eid] = 'Unknown cancellation action'
        if eid in conflicts:
            errors[eid] = 'Conflicting redelivery; original admitted business history retained'
        if eid in errors:
            iid = issue(e['Cancellation reference'], int(e['Trip revision']), eid, errors[eid], 'Administration / Supervisor',
                        'Supply an unambiguous matching initiation/confirmation, exact target and authorized actor; do not infer ordering.', [refs(e)])
            if e['Cancellation reference'] in states:
                states[e['Cancellation reference']]['issue_record_ids'].append(iid)
                states[e['Cancellation reference']]['next_owner']='Administration / Supervisor'
    for e in deliveries:
        eid = e['Cancellation activity reference']
        observations.append(dict(e, admitted=eid in admitted and payload(e)==payload(unique_events[eid]), validation_error=errors.get(eid),
                                 redelivery=next(x for x in deliveries if x['Cancellation activity reference'] == eid) is not e))
    return list(states.values()), observations


def reduce_batches(data, through_batch, case_clock):
    if through_batch not in (1, 2, 3, 4):
        raise SourceError('Only original source batches 1 through 4 are supported')
    if case_clock != {'date': '2026-11-15', 'timezone': 'Europe/Amsterdam'}:
        raise SourceError('Case clock differs from reviewed source policy')
    tables = data['tables']
    if not tables.get('Finance activity'):
        raise SourceError('Unknown paid history cannot fit paid_cents; cannot seal; Finance must restore complete history')
    case_date = date.fromisoformat(case_clock['date'])
    people = unique(tables['People'], lambda r: r['Employee ID'])
    trips = unique(tables['Trips'], lambda r: (r['Trip reference'], int(r['Trip revision'])))
    receipts = unique(data['receipts'], lambda r: r['receipt_id'])
    unique(data['claims'], lambda c: (c['claim_id'], c['revision']))
    unique(tables['Review ledger'], lambda r: r['Decision reference'])
    requests, admitted, event_records, event_payloads, finance_conflicts = {}, {}, {}, {}, {}
    current, history, states, revisions, repair_history = {}, [], [], [], []
    decision_history={}
    permanent_findings = []
    for batch in range(1, through_batch + 1):
        issues = []

        def issue(subject, revision, fact, reason, owner, action, evidence=()):
            iid = f'{subject}:r{revision}:{fact}'
            if not any(i['record_id'] == iid for i in issues):
                issues.append(dict(record_id=iid, subject_id=subject, revision=revision, fact=fact, reason=reason,
                                   owner=owner, resolution_needed=action, source_refs=list(evidence), status='open', run_batch=str(batch)))
            return iid

        arrivals = sorted((c for c in data['claims'] if int(c['batch_id']) == batch), key=lambda c: (c['claim_id'], c['revision']))
        for card in arrivals:
            cid = card['claim_id']
            old = current.get(cid)
            if old and card['revision'] <= old['revision']:
                raise SourceError(f'{cid}: non-increasing claim revision')
            if old:
                old_lines = {l['cost_id']: l for l in old['lines']}
                for line in card['lines']:
                    if line['cost_id'] in old_lines and line['first_submitted'] != old_lines[line['cost_id']]['first_submitted']:
                        permanent_findings.append((cid, card['revision'], 'filing_history:'+line['cost_id'], 'Unchanged cost changed its initial filing date', card))
                changed = [k for k in ('employee_id', 'trip_id', 'trip_revision', 'submitted', 'status', 'reason', 'lines', 'exception') if old.get(k) != card.get(k)]
                previous = next(c for c in states[-1]['claims'] if c['claim_id'] == cid) if states else None
                revisions.append(dict(claim_id=cid, from_revision=old['revision'], to_revision=card['revision'], arrival_batch=str(batch),
                                      changed_fields=changed, invalidated_decision_ids=previous['decision_ids'] if previous else [],
                                      retained_cost_ids=[l['cost_id'] for l in card['lines'] if old_lines.get(l['cost_id']) == l],
                                      reason='Recheck changed dependencies and exact revision authority; broaden when prior validity cannot be shown.',
                                      source_refs=[refs(old), refs(card)]))
                for req in requests.values():
                    if req['claim_id'] == cid:
                        req['resolution_required'] = True
                        req['resolution_triggers'].append({'kind': 'material_correction', 'revision': card['revision'], 'batch': str(batch)})
                        req['resolution_event_id'] = None
            current[cid] = card
            history.append(card)
        for cid, revision, fact, why, card in permanent_findings:
            issue(cid, revision, fact, why, 'Administration', 'Restore preserved original filing evidence for this cost; do not move the deadline.', [refs(card)])
        cancellations, cancellation_events = cancellation_view(data, batch, history, requests, people, trips, issue, case_date)
        decisions, permits, permit_map, travel_bases = [], [], {}, []
        for key, trip in trips.items():
            if trip['Employee ID'] not in people:
                raise SourceError('Unknown trip employee: '+trip['Employee ID'])
            person = people[trip['Employee ID']]
            affected = [c for c in cancellations if (c['trip_id'], c['trip_revision']) == key]
            permission, trip_status = 'not-required', 'active'
            if trip['International'] == 'True':
                result = review('permit', trip['Permit reference'], int(trip['Permit revision']), trip, person,
                                cents(trip['Estimate (EUR)']), [], tables, batch, case_date)
                permit_map[key] = result
                decisions.extend(result['records'])
                permission = result['outcome']
            for c in affected:
                if c['status'] == 'requested':
                    trip_status, permission = 'arrangements-paused', 'paused'
                else:
                    if c['target_type'] == 'trip':
                        trip_status = 'retired'
                    permission = 'retired' if trip['Permit reference'] else 'not-required'
            if trip['International'] == 'True':
                permits.append(dict(permit_id=trip['Permit reference'], revision=int(trip['Permit revision']), trip_id=key[0], trip_revision=key[1],
                                    estimate_cents=cents(trip['Estimate (EUR)']), status=result['outcome'], current_permission=permission,
                                    decision_ids=result['decision_ids'], evidence=[refs(trip)]))
            travel_bases.append(dict(trip_id=key[0], trip_revision=key[1], status=trip_status, permission=permission,
                                     cancellation_ids=[c['cancellation_id'] for c in affected], source_refs=[refs(trip)]))
        claims = []
        for cid, card in sorted(current.items()):
            key = (card['trip_id'], card['trip_revision'])
            trip = trips.get(key)
            if not trip or trip['Employee ID'] != card['employee_id']:
                raise SourceError(cid+': trip/employee identity mismatch; Administration must repair')
            person = people[card['employee_id']]
            affected = [c for c in cancellations if (c['trip_id'], c['trip_revision']) == key]
            lines = [line_review(card, line, trip, person, receipts, tables, permit_map.get(key), affected) for line in card['lines']]
            for line, finding in zip(card['lines'], lines):
                prior = [r for r in requests.values() if r['claim_id'] != cid and line['cost_id'] in r['cost_ids']]
                if prior:
                    r = prior[0]
                    matching = r['employee_id'] == card['employee_id'] and (r['trip_id'], r['trip_revision']) == key
                    if len(prior) == 1 and matching and r['claim_id'] in card['related_claim_ids'] and r['net_paid_cents'] == r['amount_cents'] and r['amount_cents'] > 0 and not r['resolution_required']:
                        finding.update(status='excluded', allowed_cents=0, reason='Already settled under related original obligation; excluded from new reimbursement',
                                       original_request_id=r['request_id'], original_claim_id=r['claim_id'])
                    else:
                        finding.update(status='unresolved', allowed_cents=None, reason='Prior cost obligation requires Finance linkage/disposition')
                        finding['findings'].append('prior_cost_obligation')
                for fact in finding['findings']:
                    owner = 'Finance' if any(t in fact for t in ('fx_', 'cap_', 'late_', 'permit_', 'category_', 'exception', 'cancellation', 'obligation')) else card['employee_id']+' / Administration'
                    issue(cid, card['revision'], line['cost_id']+':'+fact, line['cost_id']+': '+fact, owner,
                          repair_action(card, line, fact, trip), finding['evidence'])
            allowed = sum(l['allowed_cents'] for l in lines) if all(l['allowed_cents'] is not None for l in lines) else None
            reviewed_amount = allowed if allowed is not None else (sum(l.get('arithmetic_cents', 0) for l in lines) if all(l.get('arithmetic_cents') is not None for l in lines) else None)
            rev = review('claim', cid, card['revision'], trip, person, reviewed_amount, [l['cost_id'] for l in lines], tables, batch, case_date, affected)
            decisions.extend(rev['records'])
            c = dict(claim_id=cid, revision=card['revision'], trip_id=key[0], trip_revision=key[1], employee_id=card['employee_id'],
                     status='pending', lines=lines, allowed_cents=allowed, paid_cents=0, balance_cents=None,
                     decision_ids=rev['decision_ids'], next_owner=None, reason='Awaiting current review', approval_status=rev['outcome'],
                     approval_at=rev['approved_at'], source_refs=[refs(card)], closure_candidate=False, issue_record_ids=[],
                     reviewed_arithmetic_cents=reviewed_amount)
            if card['status'] == 'withdrawn' or rev['outcome'] == 'reject':
                c.update(status='withdrawn' if card['status']=='withdrawn' else 'rejected', allowed_cents=0,
                         reason=card['reason'] if card['status']=='withdrawn' else 'Authorized rejection: '+next(r['Reason'] for r in rev['records'] if r['Outcome']=='reject' and r['admitted']))
            elif rev['outcome'] == 'return':
                r = next(r for r in rev['records'] if r['Outcome']=='return' and r['admitted'])
                issue(cid, card['revision'], 'review_return', r['Reason'], card['employee_id']+' / '+r['Reviewer'], r['Repair requested'], [refs(r)])
            elif allowed is not None and allowed > 0 and rev['outcome'] != 'approved' or any('cancellation' in p for p in rev['problems']):
                issue(cid, card['revision'], 'review_authority', '; '.join(rev['problems']) or 'Current approval missing',
                      'Administration / authorized reviewers', f"Obtain valid current {cid} r{card['revision']} responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision.", [refs(card)])
            for cancel in affected:
                if cancel['issue_record_ids']:
                    issue(cid, card['revision'], 'cancellation_integrity:'+cancel['cancellation_id'], 'Cancellation contains unresolved invalid/conflicting deliveries',
                          'Administration / Supervisor', 'Resolve the cancellation event/target/authority conflict before releasing dependent work.', cancel['source_refs'])
                if cancel['status'] == 'requested':
                    issue(cid, card['revision'], 'travel_cancellation:'+cancel['cancellation_id'], 'Cancellation requested; readiness paused, not confirmed',
                          cancel['next_owner'], f"Supervisor must confirm or resolve {cancel['cancellation_id']} against its exact initiation; retain original Finance commitment.", cancel['source_refs'])
            claims.append(c)
        by_claim = {c['claim_id']: c for c in claims}
        for d in decisions:
            if d['admitted'] and d['Decision reference'] not in decision_history:
                decision_history[d['Decision reference']]=dict(d,first_validated_batch=str(batch))
        # Old decisions remain history, not current authorization.
        current_decision_ids = {d['Decision reference'] for d in decisions}
        for d in tables['Review ledger']:
            if int(d['Arrival batch']) <= batch and d['Decision reference'] not in current_decision_ids:
                decisions.append(dict(d, admitted=False, historical=True, validation_errors=['not current subject/revision authority'],
                                      packet=next((p for p in tables['Review packets'] if p['Decision reference']==d['Decision reference']), None)))
        for cancel in cancellations:
            if cancel['status'] == 'confirmed':
                for r in requests.values():
                    if (r['trip_id'], r['trip_revision']) == (cancel['trip_id'], cancel['trip_revision']) and timestamp(r['accepted_at']) <= timestamp(cancel['confirmed_at']):
                        trigger = {'kind':'travel_cancellation', 'cancellation_id':cancel['cancellation_id'], 'batch':str(batch)}
                        if not any(t.get('cancellation_id')==cancel['cancellation_id'] for t in r['resolution_triggers']):
                            r['resolution_required'] = True
                            r['resolution_triggers'].append(trigger)
                            r['resolution_event_id'] = None
        _finance(data, batch, case_date, people, current, by_claim, requests, admitted, event_records, event_payloads, finance_conflicts, issues, issue)
        for c in claims:
            own_requests = [r for r in requests.values() if r['claim_id']==c['claim_id']]
            c['paid_cents'] = sum(r['net_paid_cents'] for r in own_requests)
            c['request_ids'] = [r['request_id'] for r in own_requests]
            for r in own_requests:
                if r['retry_required']:
                    issue(c['claim_id'], c['revision'], 'finance_retry', 'Finance attempt failed; no transfer effect', 'Finance', f"Supply explicit retry authorization for {r['request_id']} before another attempt.", r['source_refs'])
                if r['status']=='cancel-pending':
                    issue(c['claim_id'], c['revision'], 'finance_cancel', 'Finance cancellation requested, not confirmed', 'Finance', f"Confirm cancellation/status of original {r['request_id']}; hold competing replacements.", r['source_refs'])
                if r['resolution_required'] and not r['resolution_event_id']:
                    issue(c['claim_id'], c['revision'], 'finance_resolution:'+r['request_id'], 'Original obligation requires explicit Finance reconciliation/resolution', 'Finance', f"Resolve {r['request_id']} against current entitlement and its original trip/cost basis; reconcile any linked refund/late transfer. A matching total alone is insufficient.", r['source_refs'])
                if r['trip_id'] != c['trip_id'] or r['trip_revision'] != c['trip_revision']:
                    if r['net_paid_cents'] or r['amount_cents'] or r['resolution_required']:
                        issue(c['claim_id'], c['revision'], 'prior_request_basis:'+r['request_id'], f"{r['request_id']} belongs to prior {r['trip_id']} r{r['trip_revision']}; transfers cannot be assigned to replacement costs", 'Finance / Administration',
                              'Confirm original financial disposition and current trip authority before releasing a replacement request.', r['source_refs'])
            if c['allowed_cents'] is not None and (c['approval_status']=='approved' or c['allowed_cents']==0):
                c['balance_cents'] = c['allowed_cents'] - c['paid_cents']
            if c['balance_cents'] is not None and c['balance_cents']<0:
                issue(c['claim_id'], c['revision'], 'overpayment', 'Confirmed net transfers exceed current supported entitlement', 'Finance',
                      'Supply a linked confirmed refund and explicit resolution; refund promises do not change paid money.')
            own = [i for i in issues if i['subject_id']==c['claim_id']]
            if own:
                c.update(status='held', next_owner=own[0]['owner'], reason='; '.join(i['reason'] for i in own), issue_record_ids=[i['record_id'] for i in own])
            elif c['status'] in ('withdrawn','rejected'):
                if c['paid_cents'] or any(r['amount_cents']>r['net_paid_cents'] for r in own_requests):
                    iid=issue(c['claim_id'],c['revision'],'nonpayment_finance_effect','Withdrawal/rejection retains financial obligations','Finance','Resolve the original request and any actual transfer; do not erase payment.')
                    c.update(status='held', next_owner='Finance', reason='Non-payment outcome still has financial effects',issue_record_ids=[iid])
            elif c['allowed_cents']==0:
                c.update(status='closed-no-payment',next_owner=None,reason='Known zero entitlement with no unresolved financial effect')
            elif c['approval_status']=='approved' and c['allowed_cents'] is not None:
                complete = c['balance_cents']==0 and all(r['amount_cents']==r['net_paid_cents'] and not r['retry_required'] and (not r['resolution_required'] or r['resolution_event_id']) for r in own_requests)
                c.update(status='closed-reimbursed' if complete else ('ready' if c['paid_cents']==0 else 'pending'), next_owner=None if complete else 'Finance',
                         closure_candidate=complete, reason='Current authority, entitlement, net transfers and required Finance resolutions agree; no outstanding issue' if complete else 'Finance: settle the current authorized outstanding balance without duplicating its obligation')
            c['supported_cents']=sum(l['allowed_cents'] or 0 for l in c['lines'] if l['status']=='supported')
            c['payable_cents']=max(0,c['balance_cents'] or 0) if not own and c['approval_status']=='approved' else 0
            c['held_cents']=max(sum(max(0,r['amount_cents']-r['net_paid_cents']) for r in own_requests), max(0,c['balance_cents'] or 0)) if own else 0
            c['held_amount_unknown']=bool(own and c['allowed_cents'] is None)
            c['finance_outstanding_cents']=sum(max(0,r['amount_cents']-r['net_paid_cents']) for r in own_requests)
            c['unreconciled_paid_cents']=sum(r['net_paid_cents'] for r in own_requests if r['resolution_required'] and not r['resolution_event_id'] and (c['balance_cents'] is None or r['trip_id']!=c['trip_id']))
        for cancel in cancellations:
            key=(cancel['trip_id'],cancel['trip_revision'])
            cancel['original_request_ids']=[r['request_id'] for r in requests.values() if (r['trip_id'],r['trip_revision'])==key]
            related=[by_claim[c] for c in cancel['affected_claim_ids'] if c in by_claim]
            if cancel['financial_status']=='unresolved':
                related_requests=[requests[r] for r in cancel['original_request_ids']]
                resolved=cancel['status']=='confirmed' and not cancel['issue_record_ids'] and related and all(c['status'] in ('closed-reimbursed','closed-no-payment') for c in related) and all(not r['resolution_required'] or r['resolution_event_id'] for r in related_requests)
                if resolved:
                    cancel.update(financial_status='resolved',next_owner=None,reason='Cancellation-aware cost disposition and current review/Finance reconciliation complete')
                else:
                    iid=issue(cancel['cancellation_id'],cancel['trip_revision'],'financial_disposition','Cancellation has costs or obligations; business confirmation alone does not resolve them','Finance / Administration',
                              'Review linked claims, original requests, scoped cancellation disposition and current packet context; obtain required Finance resolution after prior acceptance.',cancel['source_refs'])
                    cancel['issue_record_ids'].append(iid)
                    if cancel['status']=='confirmed':cancel['next_owner']='Finance / Administration'
        prior_issues = states[-1]['issues'] if states else []
        old_by_fact={(i['subject_id'],i['fact']):i for i in prior_issues}
        new_by_fact={(i['subject_id'],i['fact']):i for i in issues}
        for key,i in new_by_fact.items():
            old=old_by_fact.get(key)
            if old and old['record_id']!=i['record_id']:
                i['previous_record_ids']=[old['record_id']]
                repair_history.append(dict(batch_id=str(batch),action='carried',record_id=i['record_id'],previous_record_id=old['record_id'],reason='Same missing fact remains unsupported on current revision'))
            elif not old:
                repair_history.append(dict(batch_id=str(batch),action='opened',record_id=i['record_id'],reason=i['reason']))
        for key,i in old_by_fact.items():
            if key not in new_by_fact:
                card=current.get(i['subject_id'])
                replacement=card and any(i['fact'].startswith(l['cost_id']+':') for h in history if h['claim_id']==card['claim_id'] and h['revision']<card['revision'] for l in h['lines']) and not any(i['fact'].startswith(l['cost_id']+':') for l in card['lines'])
                repair_history.append(dict(batch_id=str(batch),action='superseded' if replacement else 'resolved',record_id=i['record_id'],
                                           reason='Changed travel/cost basis supersedes the old issue; original missing evidence is not invented' if replacement else 'Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain',
                                           source_refs=[refs(card)] if card else [], finance_event_ids=[eid for eid,e in admitted.items() if int(e['Arrival batch'])==batch and e['Claim reference']==i['subject_id']]))
        finance_deliveries=[e for e in tables['Finance activity'] if int(e['Arrival batch'])<=batch]
        finance_events=[dict(e, admitted=e['Activity reference'] in admitted and payload(e)==event_payloads[e['Activity reference']],
                             validation_error=event_records.get(e['Activity reference']),redelivery=next(x for x in finance_deliveries if x['Activity reference']==e['Activity reference']) is not e) for e in finance_deliveries]
        state=dict(presentation_version=4, claims=claims, requests=list(requests.values()), travel_cancellations=cancellations,
                   admitted_event_ids=list(admitted), issues=issues, decisions=decisions, permits=permits, trips=tables['Trips'],travel_bases=travel_bases,
                   finance_events=finance_events,cancellation_events=cancellation_events,budget=_budget(tables,people,requests),
                   claim_history=history,revision_history=revisions,repair_history=repair_history,decision_history=list(decision_history.values()),
                   coverage={'through_batch':batch,'delivered_claims':len(current),'delivered_claim_revisions':len(history),
                             'review_deliveries':sum(int(r['Arrival batch'])<=batch for r in tables['Review ledger']),
                             'finance_deliveries':len(finance_deliveries),'cancellation_deliveries':sum(int(r['Arrival batch'])<=batch for r in tables['Travel cancellations']),
                             'deferred_batches':list(range(batch+1,5)),'status':'all-source-batches' if batch==4 else 'partial-batches',
                             'limits':['Unresolved cases are owned operational outcomes','G3 final owner review and handoff acceptance pending']})
        states.append(deepcopy(state))
    return states


def _budget(tables, people, requests):
    result=[]
    for group in sorted({tuple(p[k] for k in ('Department','Project','Budget period')) for p in people.values()}):
        base=[r for r in tables['Budget'] if tuple(r[k] for k in ('Department','Project','Budget period'))==group]
        allocated=sum(cents(r['Allocation or commitment (EUR)']) for r in base if r['Entry type']=='allocation')
        net=sum(cents(r['Settled (EUR)'])-cents(r['Refunded (EUR)']) for r in base if r['Entry type']=='obligation')
        remaining=sum(max(0,cents(r['Allocation or commitment (EUR)'])-(cents(r['Settled (EUR)'])-cents(r['Refunded (EUR)']))) for r in base if r['Entry type']=='obligation')
        included=[r for r in requests.values() if tuple(people[r['employee_id']][k] for k in ('Department','Project','Budget period'))==group]
        net+=sum(r['net_paid_cents'] for r in included)
        remaining+=sum(max(0,r['amount_cents']-r['net_paid_cents']) for r in included)
        result.append(dict(department=group[0],project=group[1],period=group[2],allocation_cents=allocated,net_settled_cents=net,
                           remaining_commitments_cents=remaining,available_cents=allocated-net-remaining,source_refs=[refs(r) for r in base],accepted_request_ids=[r['request_id'] for r in included]))
    return result


def _finance(data, batch, case_date, people, current, claims, requests, admitted, errors, seen, conflicts, issues, issue):
    deliveries=[e for e in data['tables']['Finance activity'] if int(e['Arrival batch'])<=batch]
    first={}
    for e in sorted(deliveries,key=lambda e:(int(e['Arrival batch']),e['_locator'])):
        eid=e['Activity reference']
        if eid not in seen:
            seen[eid]=payload(e)
        elif seen[eid]!=payload(e):
            conflicts[eid]=e
        if eid not in first and seen[eid]==payload(e):
            first[eid]=e
    priority={'accepted':0,'failed':1,'retry_authorized':2,'cancellation_requested':3,'cancelled':4,'adjustment':5,'settled':6,'refund':7,'resolution':8}
    pending=sorted((e for eid,e in first.items() if eid not in admitted),key=lambda e:(int(e['Arrival batch']),timestamp(e['Activity time (UTC)']),priority.get(e['Activity type'],99),e['Activity reference']))
    # A linked event may arrive before its basis. Retry only while an admission
    # establishes new evidence; no duplicate effects from repeated deliveries.
    changed=True
    while changed:
        changed=False
        for e in pending:
            eid,cid,rid,kind=e['Activity reference'],e['Claim reference'],e['Request reference'],e['Activity type']
            if eid in admitted:
                continue
            c=claims.get(cid)
            req=requests.get(rid)
            error=None
            person=people.get(req['employee_id'] if req else c['employee_id'] if c else '')
            if eid in conflicts and int(first[eid]['Arrival batch'])==batch:
                if kind in ('settled','refund'):
                    raise SourceError('Conflicting first-delivered payment amount cannot establish paid_cents; Finance must resolve '+eid+' before sealing')
                error='Conflicting first-delivered Finance payload; no basis selected from sheet row order'
            elif not c or not person:
                error='Unmatched claim or employee; retain event for later basis'
            elif e['Finance officer']!=person['Finance officer'] or e['Payee ID']!=person['Payee ID'] or e['Currency']!='EUR':
                error='Wrong Finance actor, payee or currency'
            elif not e['Reason']:
                error='Finance event has no reason'
            elif timestamp(e['Activity time (UTC)']).astimezone(ZoneInfo('Europe/Amsterdam')).date()>case_date:
                error='Future Finance observation'
            elif req and (req['claim_id']!=cid or timestamp(e['Activity time (UTC)'])<timestamp(req['accepted_at'])):
                error='Wrong request/claim or event predates acceptance'
            elif kind=='accepted':
                amount=cents(e['Obligation (EUR)'],exact=True)
                blockers=[i for i in issues if i['subject_id']==cid]
                competing=[r for r in requests.values() if r['claim_id']==cid and (r['amount_cents']>r['net_paid_cents'] or r['status'] in ('dispatched','cancel-pending') or r['resolution_required'] and not r['resolution_event_id'])]
                if req or amount<=0 or c['allowed_cents']!=amount or c['approval_status']!='approved' or blockers or competing or timestamp(e['Activity time (UTC)'])<timestamp(c['approval_at']):
                    error='Acceptance cannot bind an unblocked current authorized obligation; conflicting/missing basis'
                else:
                    req=dict(request_id=rid,claim_id=cid,revision=c['revision'],employee_id=c['employee_id'],trip_id=c['trip_id'],trip_revision=c['trip_revision'],
                             amount_cents=amount,original_amount_cents=amount,payee=person['Payee ID'],currency='EUR',status='accepted',
                             decision_ids=c['decision_ids'],accepted_at=e['Activity time (UTC)'],accepted_batch=e['Arrival batch'],event_ids=[],
                             cost_ids=[l['cost_id'] for l in c['lines'] if l['status']!='excluded'],cost_amounts={l['cost_id']:l['allowed_cents'] for l in c['lines'] if l['status']!='excluded'},
                             source_refs=[refs(e)],net_paid_cents=0,settlement_ids=[],refunded_by_settlement={},retry_required=False,
                             resolution_required=False,resolution_event_id=None,resolution_triggers=[],basis_history=[{'revision':c['revision'],'amount_cents':amount,'event_id':eid}])
                    requests[rid]=req
            elif not req:
                error='Unmatched original Finance request; retain event for later basis'
            elif kind=='settled':
                amount=cents(e['Amount (EUR)'],exact=True)
                if amount<=0 or req['retry_required']:
                    error='Transfer amount invalid or explicit retry authorization missing'
                else:
                    late=req['status']=='cancelled'
                    req['net_paid_cents']+=amount
                    req['settlement_ids'].append(eid)
                    req['status']='settled' if req['net_paid_cents']>=req['amount_cents'] else 'dispatched'
                    if late or req['net_paid_cents']>req['amount_cents']:
                        req['resolution_required']=True
                        req['resolution_event_id']=None
                        req['resolution_triggers'].append({'kind':'late_transfer' if late else 'overpayment','event_id':eid,'batch':str(batch)})
            elif kind=='failed':
                req.update(status='held',retry_required=True,last_failure_at=e['Activity time (UTC)'])
            elif kind=='retry_authorized':
                if not req['retry_required'] or timestamp(e['Activity time (UTC)'])<timestamp(req['last_failure_at']):
                    error='Retry authority lacks a prior failed attempt'
                else:
                    req.update(status='accepted',retry_required=False)
            elif kind=='cancellation_requested':
                req['status']='cancel-pending'
            elif kind=='cancelled':
                req.update(status='cancelled',amount_cents=0,retry_required=False)
                req['basis_history'].append({'revision':req['revision'],'amount_cents':0,'event_id':eid})
                if req['net_paid_cents']:
                    req['resolution_required']=True
                    req['resolution_event_id']=None
                    req['resolution_triggers'].append({'kind':'financial_cancellation_after_transfer','event_id':eid,'batch':str(batch)})
            elif kind=='adjustment':
                amount=cents(e['Obligation (EUR)'],exact=True)
                req['amount_cents']=amount
                req['basis_history'].append({'revision':c['revision'],'amount_cents':amount,'event_id':eid})
                req['resolution_required']=True
                req['resolution_event_id']=None
                req['resolution_triggers'].append({'kind':'financial_adjustment','event_id':eid,'batch':str(batch)})
            elif kind=='refund':
                amount=cents(e['Amount (EUR)'],exact=True)
                original=admitted.get(e['Original activity reference'])
                already=req['refunded_by_settlement'].get(e['Original activity reference'],0)
                if not original or original['Activity type']!='settled' or original['Request reference']!=rid or original['Claim reference']!=cid or original['Payee ID']!=e['Payee ID'] or original['Currency']!=e['Currency'] or amount<=0 or amount>cents(original['Amount (EUR)'],exact=True)-already or timestamp(e['Activity time (UTC)'])<timestamp(original['Activity time (UTC)']):
                    error='Refund lacks matching admitted transfer or exceeds unrecovered amount'
                else:
                    req['net_paid_cents']-=amount
                    req['refunded_by_settlement'][e['Original activity reference']]=already+amount
                    req['resolution_required']=True
                    req['resolution_event_id']=None
                    req['resolution_triggers'].append({'kind':'confirmed_refund','event_id':eid,'batch':str(batch)})
            elif kind=='resolution':
                amount=cents(e['Obligation (EUR)'],exact=True)
                blockers=[i for i in issues if i['subject_id']==cid]
                if amount!=req['amount_cents'] or amount!=c['allowed_cents'] or req['net_paid_cents']!=amount or c['approval_status']!='approved' or req['retry_required'] or blockers or (req['trip_id'],req['trip_revision'])!=(c['trip_id'],c['trip_revision']) or timestamp(e['Activity time (UTC)'])<timestamp(c['approval_at']):
                    error='Resolution does not reconcile current authority, entitlement, original obligation and net transfers'
                else:
                    req['resolution_event_id']=eid
                    req['status']='settled'
            else:
                error='Unsupported Finance activity type: '+kind
            if error:
                errors[eid]=error
            else:
                admitted[eid]=e
                errors[eid]=None
                req['event_ids'].append(eid)
                if refs(e) not in req['source_refs']:
                    req['source_refs'].append(refs(e))
                changed=True
    for eid,e in first.items():
        if eid not in admitted:
            c=claims.get(e['Claim reference'])
            issue(e['Claim reference'],c['revision'] if c else 1,'finance_event:'+eid,errors.get(eid) or 'Unadmitted Finance event','Finance',
                  f"Resolve {eid} against request {e['Request reference']}, exact payee/currency/time and source authority; no transfer effect is invented.",[refs(e)])
    for eid,e in conflicts.items():
        c=claims.get(e['Claim reference'])
        issue(e['Claim reference'],c['revision'] if c else 1,'finance_conflict:'+eid,'Conflicting immutable Finance payload; original admitted money retained','Finance',
              'Supply an authoritative resolution of the event identity conflict; do not overwrite history.',[refs(e)])

"""Deterministic operational views and independent artifact integrity checks."""
import csv
import hashlib
import io
import json
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from source_io import SourceError

HEADER = ['claim_id', 'revision', 'trip_id', 'status', 'allowed_cents', 'paid_cents', 'balance_cents', 'next_owner', 'reason']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def csv_text(state):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=HEADER, lineterminator='\n')
    writer.writeheader()
    writer.writerows({k: c[k] for k in HEADER} for c in state['claims'])
    return stream.getvalue()


def safe(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def eur(value):
    return 'unknown' if value is None else f'{value / 100:.2f}'


def financial_summary(state):
    held = [c for c in state['claims'] if c['status']=='held']
    return {
        'payable_cents': sum(c.get('payable_cents', 0) for c in state['claims']),
        'known_held_entitlement_cents': sum(c['allowed_cents'] for c in held if c['allowed_cents'] is not None),
        'unknown_held_claims': sum(c['allowed_cents'] is None for c in held),
        'supported_inside_unknown_cents': sum(c.get('supported_cents', 0) for c in held if c['allowed_cents'] is None),
        'unreconciled_paid_cents': sum(c.get('unreconciled_paid_cents', 0) for c in state['claims']),
        'unsettled_commitments_cents': sum(c.get('finance_outstanding_cents', 0) for c in state['claims']),
    }


def queue_text(state):
    out = [f"# Local repair queue — {state['run_id']} / batch {state['batch_id']}", '',
           'Grouped by subject/revision; each row is one independent missing fact. Local only; no requests sent. Later supplied scenario evidence is not a reply caused by these drafts.', '',
           '| Subject/revision | Fact ID | Blocker | Owner | Evidence/action needed | Source |',
           '| --- | --- | --- | --- | --- | --- |']
    for i in sorted(state['issues'], key=lambda i: (i['subject_id'], i['revision'], i['fact'])):
        sources = ', '.join(f"{r['source_id']}: {r['locator']}" for r in i['source_refs']) or 'Cancellation links in snapshot'
        out.append('| ' + ' | '.join(safe(v) for v in [f"{i['subject_id']} r{i['revision']}", i['record_id'], i['reason'], i['owner'], i['resolution_needed'], sources]) + ' |')
    if state.get('repair_history'):
        out += ['', '## Fact history', '', '| Batch | Action | Fact | Prior fact | Evidence / reason |', '| --- | --- | --- | --- | --- |']
        for h in state['repair_history']:
            out.append('| '+' | '.join(safe(v) for v in [h['batch_id'],h['action'],h['record_id'],h.get('previous_record_id',''),h['reason']+'; Finance: '+', '.join(h.get('finance_event_ids',[]))])+' |')
    return '\n'.join(out) + '\n'


def report_text(states, manifest):
    if states[-1].get('presentation_version', 1) == 1:
        from g1_legacy_outputs import report_text as historical_report
        return historical_report(states, manifest)
    state = states[-1]
    claims = state['claims']
    exposure_view = state.get('presentation_version', 1)>=4
    unresolved = [c for c in claims if c['status'] in ('pending', 'held', 'ready')]
    out = [f"# Operations handoff — {state['run_id']} / batch {state['batch_id']}", '',
           f"Coverage: {state['coverage']['status']}. Case clock: 2026-11-15, Europe/Amsterdam; event times UTC.", '',
           f"**Payable now: EUR {eur(sum(c.get('payable_cents', 0) for c in claims))}. Known held payment balances: EUR {eur(sum(c.get('held_cents', 0) for c in claims))}.** {sum(c.get('held_amount_unknown', False) for c in claims)} held entitlement totals remain unknown; these are not zero. Confirmed net paid: EUR {eur(sum(c['paid_cents'] for c in claims))}.", '',
           'Payable means supported current entitlement with valid human approvals and no blocking issue. A held amount is not authorized for release. Accepted original Finance commitments remain visible independently of changed eligibility. These are local workflow results; no requests were sent and no money moved.', '',
           '## Payment actions', '',
           '| Claim | Payable EUR | Known held EUR | Net paid EUR | Balance EUR | Owner | Next action |',
           '| --- | ---: | ---: | ---: | ---: | --- | --- |']
    for c in sorted(unresolved, key=lambda c: (-c.get('payable_cents', 0), -c.get('held_cents', 0), c['claim_id'])):
        held_amount = c['allowed_cents'] if exposure_view and c['status']=='held' else c.get('held_cents', 0)
        if not (c.get('payable_cents') or held_amount or c.get('unreconciled_paid_cents') or (c['balance_cents'] is not None and c['balance_cents'] < 0)):
            continue
        own = [i for i in state['issues'] if i.get('subject_id') == c['claim_id']]
        action = '; '.join(i['resolution_needed'] for i in own) or 'Finance: confirm settlement against the existing obligation; do not duplicate its request.'
        out.append('| ' + ' | '.join(safe(v) for v in [c['claim_id'], eur(c.get('payable_cents', 0)), eur(held_amount), eur(c['paid_cents']), eur(c['balance_cents']), c['next_owner'] or 'None', action]) + ' |')
    out += ['', '## Blockers and supported partial evidence', '',
            '| Subject / revision | Supported line evidence EUR | Claim entitlement EUR | Blocker | Owner | Specific next action |',
            '| --- | ---: | ---: | --- | --- | --- |']
    for c in sorted(unresolved, key=lambda c: c['claim_id']):
        own = [i for i in state['issues'] if i.get('subject_id') == c['claim_id']]
        if not own:
            continue
        for i in own:
            out.append('| ' + ' | '.join(safe(v) for v in [f"{c['claim_id']} r{c['revision']}", eur(c.get('supported_cents', sum(l['allowed_cents'] or 0 for l in c['lines'] if l['status']=='supported'))), eur(c['allowed_cents']), i['reason'], i['owner'], i['resolution_needed']]) + ' |')
    out += ['', 'Supported line evidence is retained work, not permission to pay a partial incomplete claim. See the [fact-level repair queue](repair-queue.md) for source locators and stable issue IDs. Unknown CSV money is blank; known zero is 0.', '',
            '## Independent cancellations', '',
            '| Process | Target | Business state | Financial consequence | Claims / original requests | Owner |',
            '| --- | --- | --- | --- | --- | --- |']
    for c in state['travel_cancellations']:
        out.append('| ' + ' | '.join(safe(v) for v in [c['cancellation_id'], c['target_type']+' '+(c['permit_id'] if c['target_type']=='permit' else c['trip_id']), c['status'], c['financial_status'], ', '.join(c['affected_claim_ids']+c['original_request_ids']) or 'None', c['next_owner'] or 'None']) + ' |')
    out += ['', 'Cancellation confirmation must strictly follow initiation, effective at confirmation. Business cancellation does not itself cancel a Finance request or release a commitment. Permit cancellation leaves the trip active; trip cancellation retires that exact trip version and its linked permit.', '', '## Completed work and full register', '']
    done = [c for c in claims if c not in unresolved]
    out.append(f"{len(done)} of {len(claims)} current claims have a completed state; {len(unresolved)} remain unresolved. The [full CSV](claims.csv) contains exactly one current row per claim; [sealed snapshots](batches/) retain line, permission, decision and Finance evidence. Reimbursed closure requires current approvals, supported entitlement, reconciled transfers/refunds, required Finance resolutions and no outstanding issue or financial obligation. A zero balance alone never closes a case.")
    out += ['', '## Budget and changes', '']
    for b in state['budget']:
        out.append(f"{b['department']} / {b['project']} / {b['period']}: allocation EUR {eur(b['allocation_cents'])}, net settled EUR {eur(b['net_settled_cents'])}, remaining commitments EUR {eur(b['remaining_commitments_cents'])}, available EUR {eur(b['available_cents'])}. Prior obligations are included; settled portions are not subtracted twice. Funds do not replace budget approval.")
    previous = set()
    for s in states:
        current = {i['record_id'] for i in s['issues']}
        out.append(f"- [Batch {s['batch_id']}](batches/{s['batch_id']}.json): {len(s['claims'])} claims; {len(s['admitted_event_ids'])} admitted Finance IDs; {len(current)} open fact items. Added {len(current-previous)}; removed from current queue {len(previous-current)} (see retained prior snapshot and issue history).")
        previous = current
    out += ['', '## Provenance and remaining scope', '',
            'All native source observations and exact retained bytes are bound by [sources.json](sources.json). Native Notion access is unavailable; the explicitly supplied manual policy has unknown export time and unverified live equivalence. Retained-input replay is labelled offline and never described as fresh access. Same-batch simultaneous review arrivals remain subject to exact actor, role, subject, revision and packet checks; no deliberation order is invented.', '',
            'Coverage and deferred records: [coverage.json](coverage.json). ' + '; '.join(state['coverage'].get('limits', [])), '']
    if state.get('presentation_version',1)>=3:
        native_policy = next(e for e in manifest['files'] if e['source_id']=='policy-native')
        if native_policy['status']=='read':
            out = [s.replace('Native Notion access is unavailable; the explicitly supplied manual policy has unknown export time and unverified live equivalence.', 'Native policy content is retained with its observed source metadata; completeness and rule-profile checks apply to the bytes used.') for s in out]
        mode=manifest.get('mode','unknown')
        provenance=f"Source mode: **{mode}**. "
        if mode.startswith('offline'):
            provenance+=f"Retained inputs from `{manifest.get('origin_run_id','unknown')}`; no fresh native access claimed. Inspect [recomputation comparison](comparison.json) and [prior run link](prior-run.json) for divergence."
        else:
            provenance+='Fresh native attempts recorded in sources.json; manual policy is separately identified.'
        out[2:2]=[provenance,'']
        out += ['', 'Revision and issue history is retained in snapshot `claim_history`, `revision_history`, `decision_history`, and `repair_history`. Corrections revalidate affected authority even at unchanged totals; a carried missing fact stays open until its specific evidence arrives. Local drafts did not cause the supplied scenario responses.', '']
    if exposure_view:
        amounts=financial_summary(state)
        old=next(s for s in out if s.startswith('**Payable now:'))
        index=out.index(old)
        out[index:index+1]=[
            '## Financial exposure', '',
            '| Category | Amount / count | Meaning |', '| --- | ---: | --- |',
            f"| Actually payable now | EUR {eur(amounts['payable_cents'])} | Current supported entitlement, valid existing approvals, no release blocker |",
            f"| Known held entitlements (gross) | EUR {eur(amounts['known_held_entitlement_cents'])} | Reviewed amounts awaiting authority or other resolution; not authorized for payment |",
            f"| Unknown held claim totals | {amounts['unknown_held_claims']} claims | Amount unknown, not zero |",
            f"| Supported lines within unknown totals | EUR {eur(amounts['supported_inside_unknown_cents'])} | Partial evidence retained; does not establish aggregate entitlement or permit partial payment |",
            f"| Unreconciled confirmed transfers | EUR {eur(amounts['unreconciled_paid_cents'])} | Money remains on original obligations pending Finance disposition; cannot offset replacement costs |",
            f"| Unsettled accepted Finance commitments | EUR {eur(amounts['unsettled_commitments_cents'])} | Existing commitments only; zero does not mean zero unresolved exposure |", '',
            'These categories overlap and must not be added as a single balance. Gross held entitlement is not reduced by money attached to a different obligation. Confirmed net paid across claims: EUR '+eur(sum(c['paid_cents'] for c in claims))+'.',
        ]
        out=[s.replace('| Known held EUR |','| Held entitlement EUR |') for s in out]
        out += ['', '`closed-reimbursed` records that existing source-backed human approvals, entitlement and Finance facts satisfy the accepted closure conditions. The Skill validates and reports that evidence; it grants no approval, exception or payment authority.', '']
    return '\n'.join(out)


def write_views(run, states, manifest):
    run = Path(run)
    for name, text in [('claims.csv', csv_text(states[-1])), ('repair-queue.md', queue_text(states[-1])), ('report.md', report_text(states, manifest))]:
        with (run / name).open('x', encoding='utf-8', newline='') as stream:
            stream.write(text)


def verify(run, schema_path):
    run = Path(run).resolve()
    manifest = json.loads((run / 'sources.json').read_text())
    schema = json.loads(Path(schema_path).read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    def check(condition, reason):
        if not condition:
            raise SourceError('Verification failed: ' + reason)
    def bound(base, binding):
        p = (base / binding['path']).resolve()
        check(not Path(binding['path']).is_absolute() and p.is_relative_to(run) and p.is_file(), 'unsafe/missing binding path')
        check(digest(p) == binding['sha256'], 'bound file digest mismatch: ' + binding['path'])
        return p
    check(manifest['run_id'] == run.name, 'manifest run identity')
    check(not (run/'failure.json').exists(),'run contains failure diagnostic; recover into a new linked run')
    if (run/'retention.json').exists():
        seal=json.loads((run/'retention.json').read_text())
        check(seal['source_manifest_sha256']==digest(run/'sources.json'),'retained source manifest seal')
        check(seal['implementation_sha256']==digest(run/'implementation.json'),'retained implementation seal')
    ids = {e['source_id'] for e in manifest['files']}
    check(len(ids) == len(manifest['files']), 'duplicate source identity')
    for e in manifest['files']:
        if e['status'] == 'read':
            bound(run, e)
        else:
            check(e['path'] is None and e['sha256'] is None and bool(e['error']), 'unavailable source record')
    paths = sorted((run / 'batches').glob('*.json'), key=lambda p: int(p.stem))
    check([p.stem for p in paths] == [str(i) for i in range(1, len(paths)+1)] and len(paths) in (1, 2, 3, 4), 'missing/unsupported sealed batch sequence')
    previous, states = None, []
    for path in paths:
        s = json.loads(path.read_text())
        validator.validate(s)
        check(s['run_id'] == run.name and s['batch_id'] == path.stem, 'snapshot identity')
        if (run/'retention.json').exists():
            execution=json.loads((run/'executions'/path.name).read_text())
            check(execution['batch_id']==path.stem and execution['snapshot_sha256']==digest(path),'execution snapshot seal')
            check(datetime.fromisoformat(execution['sealed_at']).utcoffset() is not None,'actual execution time')
        check(bound(path.parent, s['source_binding']) == run / 'sources.json', 'source binding target')
        if previous:
            check(bound(path.parent, s['predecessor']) == previous, 'wrong predecessor')
        else:
            check(s['predecessor'] is None, 'first predecessor is not null')
        issue_ids = {i['record_id'] for i in s['issues']}
        check(len(issue_ids) == len(s['issues']), 'duplicate issue IDs')
        decision_ids = {d['Decision reference'] for d in s['decisions'] if d['admitted']}
        historical_decision_ids={d['Decision reference'] for d in s.get('decision_history',[]) if d['admitted']}
        claim_ids = {c['claim_id'] for c in s['claims']}
        check(len(claim_ids) == len(s['claims']), 'duplicate current claims')
        events = {e['Activity reference']: e for e in s['finance_events'] if e['admitted']}
        check(set(events) == set(s['admitted_event_ids']), 'Finance admitted IDs')
        for c in s['claims']:
            check(set(c['decision_ids']) <= decision_ids and set(c['issue_record_ids']) <= issue_ids, 'claim reference')
            for l in c['lines']:
                check(set(l['source_ids']) <= ids, 'line source reference')
            transfers = sum(int(Decimal(e['Amount (EUR)'])*100)*(1 if e['Activity type']=='settled' else -1) for e in events.values() if e['Claim reference'] == c['claim_id'] and e['Activity type'] in ('settled','refund'))
            check(c['paid_cents'] == transfers, 'paid differs from admitted G1 transfers' if s.get('presentation_version',1)<3 else 'paid differs from admitted net transfers/refunds')
            if c['balance_cents'] is not None:
                check(c['allowed_cents'] is not None and c['balance_cents'] == c['allowed_cents']-c['paid_cents'], 'balance arithmetic')
            if c['closure_candidate']:
                check(c['approval_status'] == 'approved' and c['balance_cents'] == 0 and not c['issue_record_ids'], 'unsupported closure candidate')
            if s.get('presentation_version',1)>=3:
                check(c['payable_cents']>=0 and (not c['payable_cents'] or c['approval_status']=='approved' and not c['issue_record_ids'] and c['balance_cents']==c['payable_cents']),'payable versus held authority')
                if c['status']=='closed-reimbursed':
                    check(c['closure_candidate'] and c['finance_outstanding_cents']==0,'financial completion')
        request_ids = {r['request_id'] for r in s['requests']}
        check(len(request_ids) == len(s['requests']), 'duplicate obligations')
        for r in s['requests']:
            check(r['claim_id'] in claim_ids and set(r['decision_ids']) <= decision_ids|historical_decision_ids and set(r['event_ids']) <= set(events), 'request reference')
            if 'net_paid_cents' in r:
                net=sum(int(Decimal(e['Amount (EUR)'])*100)*(1 if e['Activity type']=='settled' else -1) for e in events.values() if e['Request reference']==r['request_id'] and e['Activity type'] in ('settled','refund'))
                check(r['net_paid_cents']==net and net>=0,'original request payment basis')
                if r['resolution_event_id']:
                    check(r['resolution_event_id'] in events and events[r['resolution_event_id']]['Activity type']=='resolution','resolution reference')
                c=next(c for c in s['claims'] if c['claim_id']==r['claim_id'])
                if c['status']=='closed-reimbursed':
                    check(r['amount_cents']==r['net_paid_cents'] and not r['retry_required'] and (not r['resolution_required'] or r['resolution_event_id']),'unresolved Finance obligation on closed claim')
        recovered={}
        for eid,e in events.items():
            if e['Activity type']=='refund':
                original=events.get(e['Original activity reference'])
                check(original is not None and original['Activity type']=='settled' and all(e[k]==original[k] for k in ('Request reference','Claim reference','Payee ID','Currency')),'refund original transfer identity')
                recovered[e['Original activity reference']]=recovered.get(e['Original activity reference'],0)+int(Decimal(e['Amount (EUR)'])*100)
                check(0<int(Decimal(e['Amount (EUR)'])*100) and recovered[e['Original activity reference']]<=int(Decimal(original['Amount (EUR)'])*100),'refund exceeds unrecovered settlement')
        cancellation_ids = {e['Cancellation activity reference'] for e in s['cancellation_events'] if e['admitted']}
        for c in s['travel_cancellations']:
            check(set(c['admitted_cancellation_event_ids']) <= cancellation_ids and not (set(c['admitted_cancellation_event_ids']) & set(events)), 'cancellation event reference')
            check(set(c['issue_record_ids']) <= issue_ids and set(c['affected_claim_ids']) <= claim_ids and set(c['original_request_ids']) <= request_ids, 'cancellation relationship')
            if c['status'] == 'confirmed':
                check(c['confirmed_at'] > c['requested_at'] and c['effective_at'] == c['confirmed_at'], 'cancellation time')
        for b in s['budget']:
            check(b['available_cents'] == b['allocation_cents']-b['net_settled_cents']-b['remaining_commitments_cents'], 'budget arithmetic')
        states.append(s)
        previous = path
    for name, expected in [('claims.csv', csv_text(states[-1])), ('repair-queue.md', queue_text(states[-1])), ('report.md', report_text(states, manifest))]:
        check((run / name).read_text() == expected, 'view differs from sealed state: ' + name)
    coverage=json.loads((run/'coverage.json').read_text())
    check(coverage['consumed']==[s['coverage'] for s in states],'coverage snapshot consistency')
    if states[-1].get('presentation_version',1)>=3 and len(states)==4:
        check(not any(coverage[k] for k in ('deferred_claim_revisions','deferred_review_ids','deferred_finance_deliveries','deferred_cancellation_deliveries')),'unaccounted final source deliveries')
    return {'status': 'verified', 'run_id': run.name, 'snapshots': len(states), 'current_claims': len(states[-1]['claims']),
            'checks': ['public schema + formats', 'retained byte hashes', 'relative source/predecessor chain', 'money/event and issue/decision/request references', 'CSV/report/queue consistency'],
            'scope': 'Structural/semantic integrity; owner acceptance is separate from verification'}

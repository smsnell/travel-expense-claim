"""Historical G1 views retained solely to verify immutable accepted artifacts."""
import csv
import hashlib
import io
import json
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


def queue_text(state):
    out = [f"# Local repair queue — {state['run_id']} / batch {state['batch_id']}", '',
           'Grouped by subject/revision; each row is one independent missing fact. Local only; no requests sent. Later supplied scenario evidence is not a reply caused by these drafts.', '',
           '| Subject/revision | Fact ID | Blocker | Owner | Evidence/action needed | Source |',
           '| --- | --- | --- | --- | --- | --- |']
    for i in sorted(state['issues'], key=lambda i: (i['subject_id'], i['revision'], i['fact'])):
        sources = ', '.join(f"{r['source_id']}: {r['locator']}" for r in i['source_refs']) or 'Cancellation links in snapshot'
        out.append('| ' + ' | '.join(safe(v) for v in [f"{i['subject_id']} r{i['revision']}", i['record_id'], i['reason'], i['owner'], i['resolution_needed'], sources]) + ' |')
    return '\n'.join(out) + '\n'


def report_text(states, manifest):
    state = states[-1]
    claims = state['claims']
    candidates = [c for c in claims if c['closure_candidate']]
    known = [c for c in claims if c['allowed_cents'] is not None]
    pending = sum(max(0, c['balance_cents']) for c in claims if c['balance_cents'] is not None)
    overpaid = -sum(min(0, c['balance_cents']) for c in claims if c['balance_cents'] is not None)
    out = [f"# G1 preliminary report — {state['run_id']}", '',
           '**Partial implementation; original batches 1–2 consumed. G2/G3 and owner gate acceptance remain pending.**', '',
           'The fixed case clock is 2026-11-15, Europe/Amsterdam. Event times are UTC. A new run retained fresh Drive exports; the native Notion attempt failed. The manually supplied POL-2026.2 file is retained separately. Its export time and equivalence to the live page are unverified.', '',
           f"{len(claims)} current claims; {len(candidates)} financially reconciled closure candidates; {sum(c['status']=='held' for c in claims)} held. {len(state['requests'])} accepted original Finance obligations; {len(state['admitted_event_ids'])} admitted Finance facts. No money moved or external requests sent.", '',
           f"Known reviewed entitlement: EUR {eur(sum(c['allowed_cents'] for c in known))} across {len(known)} claims; {len(claims)-len(known)} claim amounts remain unknown. Confirmed net paid: EUR {eur(sum(c['paid_cents'] for c in claims))}. Known positive authorized balances: EUR {eur(pending)}; known overpayment: EUR {eur(overpaid)}. Unknown balances are excluded from these subtotals, never treated as zero.", '',
           'Financially reconciled candidates remain `ready` with `closure_candidate: true`, pending the owner’s D4 presentation/delivery decision. They require no duplicate payment request. Existing human approvals are scenario evidence; the runner grants none.', '',
           '## Current claims (EUR)', '',
           '| Claim / revision | Status | Reviewed entitlement | Net paid | Authorized balance | Next owner | Reason |',
           '| --- | --- | ---: | ---: | ---: | --- | --- |']
    for c in claims:
        out.append('| ' + ' | '.join(safe(v) for v in [f"{c['claim_id']} r{c['revision']}", c['status'], eur(c['allowed_cents']), eur(c['paid_cents']), eur(c['balance_cents']), c['next_owner'] or 'None', c['reason']]) + ' |')
    out += ['', '## Evidence and permission', '',
            'Review timestamps are reply-arrival observations (interview D-4, 04:35–04:40). Required stages must be valid for the same subject/revision. Equal timestamps are accepted only within the same arrival batch; different timestamps must preserve dependent order. Combined budget/supervisor responses require the same authorized actor and both roles. Cancellation retains strictly later confirmation and effective=occurred.', '',
            'Line findings retain individual receipt/merchant/rate/cap locators and supported arithmetic even when the aggregate claim is held. The snapshots’ `decisions` retain original ledger rows, packets, actor checks and rejected imports; `finance_events` retain original request/time/amount evidence. CSV unknown amounts are blank; snapshot unknowns are null.', '',
            '| Permit / revision | Trip | Estimate EUR | Historical review status | Current permission |',
            '| --- | --- | ---: | --- | --- |']
    for p in state['permits']:
        out.append(f"| {p['permit_id']} r{p['revision']} | {p['trip_id']} | {eur(p['estimate_cents'])} | {p['status']} | {p.get('current_permission',p['status'])} |")
    out += ['', '## Independent cancellation processes', '',
            '| Cancellation | Target | State | Affected claims | Original Finance requests | Financial consequence | Next owner |',
            '| --- | --- | --- | --- | --- | --- | --- |']
    for c in state['travel_cancellations']:
        out.append('| ' + ' | '.join(safe(v) for v in [c['cancellation_id'], f"{c['target_type']} {c['permit_id'] if c['target_type']=='permit' else c['trip_id']}", c['status'], ', '.join(c['affected_claim_ids']) or 'None', ', '.join(c['original_request_ids']) or 'None', c['financial_status'], c['next_owner'] or 'None']) + ' |')
    out += ['', 'No synthetic claim is created for an independent trip cancellation. Business confirmation never releases an accepted Finance commitment. Permit-only cancellation leaves the trip active; trip cancellation retires that exact trip version and linked permit.', '', '## Budget view', '']
    for b in state['budget']:
        out.append(f"{b['department']} / {b['project']} / {b['period']}: allocation EUR {eur(b['allocation_cents'])}; net settled EUR {eur(b['net_settled_cents'])}; remaining commitments EUR {eur(b['remaining_commitments_cents'])}; available EUR {eur(b['available_cents'])}. Includes supplied prior obligations and all accepted requests; settled portions are not subtracted twice. Funds do not substitute for human budget approval.")
    out += ['', '## Batch and queue changes', '']
    previous = None
    for s in states:
        old = {i['record_id'] for i in previous['issues']} if previous else set()
        now = {i['record_id'] for i in s['issues']}
        out.append(f"- [Batch {s['batch_id']}](batches/{s['batch_id']}.json): {len(s['claims'])} current claims; {len(s['admitted_event_ids'])} admitted Finance facts; {len(s['issues'])} open fact items. Added: {', '.join(sorted(now-old)) or 'none'}. Resolved: {', '.join(sorted(old-now)) or 'none'}. Prior sealed snapshot retained.")
        previous = s
    out += ['', 'See [repair queue](repair-queue.md) for each blocker, owner, precise missing fact/action and source locator. [claims.csv](claims.csv) has one current row per claim. [sources.json](sources.json) binds all retained original bytes; [coverage.json](coverage.json) inventories delivered and deferred records.', '',
            '## D4 recommendation for owner review', '',
            'After inspecting these actual outputs, accept the proposed distinction: closure requires current authorized entitlement, confirmed net transfers/refunds, all source-required resolutions and no remaining relevant issue. Deliver the full four-batch assignment with explicit unresolved cases where evidence stops. This gives Operations a truthful partial result without presenting missing evidence as financial completion. Acceptance check: inspect C01/C02 matching entitlement/payment, C16/C120 partial settlement, C20 overpayment, C114 unknown total with its supported line intact, and TC122 without a claim. C19/C121 correction/resolution distinctions remain G2 checks. No D4 decision is presumed.', '',
            '## Remaining scope and retry', '',
            'G2 implements batches 3–4, corrections and partial-response queue history, retry/refund/resolution and remaining cancellations, offline replay, resume and recovery. Those commands currently fail explicitly. G3 covers final integrated/operational verification and submission. This G1 run is not final assignment completion. Do not overwrite sealed snapshots; changed inputs or implementation require a new linked run. Owner manages coding-session capture verification.', '']
    return '\n'.join(out)


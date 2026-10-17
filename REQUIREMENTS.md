# Project D — Travel Expense Claim

## Purpose and source of truth

Build a reusable Agent Skill for Alderbridge Consulting's fictional travel-expense process. The Skill must give Operations a traceable view of work completed, work still blocked, monetary obligations, human decisions, and the next action when claims or travel arrangements change.

This document specifies the assignment's required behavior and artifacts. The stakeholder interview and five native sources establish **company-specific rules** (including field meanings, approval boundaries, dates, currencies, and completion criteria). Do not invent or infer missing policy to make a case appear complete. Escalate missing, conflicting, or inaccessible required evidence to the operations lead or facilitator and identify the affected scope.

The repository's `snapshot.schema.json` is the authoritative contract for snapshot fields, types, enumerations, and references. Do not replace it with an invented simplified schema.

## 1. Inputs and source integrity

- Obtain the **five native source locations** through the stakeholder interview. Sources include searchable PDFs, a Google Sheets workbook, and a Notion page; the starter repository does not contain the business data.
- Preserve the **supplied case clock**, the arrival-batch sequence and boundaries, and the original identities, revisions, wording, precision, and relevant history of records.
- **Every new run must attempt fresh access to all five locations**, using a browser or supported API/export route. Do not silently use bundled data, older downloads, or model-generated summaries as replacements.
- Retain the complete relevant source content actually used, in files under that run, and bind those exact retained bytes in `sources.json`.
- Record missing, inaccessible, partial, or incompatible material explicitly, including the specific affected scope. A reachable URL, HTTP success, or SHA-256 alone does not prove full access.
- Support explicitly labelled **offline replay** from a previous run's retained inputs. Never describe replay as a fresh source read.
- Do not alter original sources or fabricate business decisions, evidence, identities, or source versions.

## 2. Required business workflow

Process all supplied records and arrival batches, including:

1. Travel permission and trip/permit handling, including revisions.
2. Expense-claim intake, line review, and monetary validation.
3. Authorized human decisions and returned or incomplete work.
4. Reimbursement-event reconciliation, outstanding balances, and closure under source-defined rules.
5. Corrections and revalidation of materially dependent work.
6. Trip or permit cancellations **independently of claims**, including cancellations for which no claim exists.
7. Later evidence and partially resolving responses, without retroactively treating them as caused by locally drafted requests.

Build and demonstrate one connected ordinary path before covering the material exception branches. The Skill may leave individual cases unresolved if the records do not support completion. Every unresolved item must identify what is affected, why it is blocked, the responsible person or role, and the evidence or action needed to resume.

### State and money invariants

- Preserve distinct subject, trip/permit, claim, revision, decision, request, obligation, financial-event, issue, and source identities as applicable to the schema and records.
- Preserve links from monetary findings, decisions, transitions, and outputs to the source records and revisions that support them.
- Do not conflate a claim's approval, eligibility, payment, reimbursement reconciliation, and closure; apply the distinctions established in the sources.
- Money in required outputs is **integer EUR cents** or `null` when unknown. In `claims.csv`, unknown money is blank. **Zero is known, not missing.**
- Calculate amounts and transitions deterministically where possible, and validate the inputs to any model-assisted interpretation. Do not embed case-specific answers in implementation code.
- Where a claim is incomplete, prevent only the work that the confirmed business rules make dependent on that missing information; retain independent work when valid. Make the dependency and remaining blocker visible.
- Revalidate affected downstream findings and outputs after material corrections. Do not discard valid unrelated work or erase earlier recorded history.

## 3. Human authority and local repair work

- People retain approval, exception, and payment authority. The Skill may validate and consume **authorized scenario decisions** and record their consequences; it may not invent replies, recommend professional approval outcomes, send real requests, book travel, or transfer money.
- Provide a **local repair queue and/or request drafts** for missing evidence and returned work. Apply the same organization consistently to relevant records.
- Each item must be traceable to its subject, revision, source, missing fact or return reason, responsible person/role, and next action. Keep stable identities and appropriate links to decisions and events.
- A partial response may resolve **only the specific facts it supports**. Unsupported portions and unrelated requests remain open; reflect consequential queue updates across later batches.
- Show significant queue changes, including run and batch references, in `report.md` or through clearly linked local queue views. Drafts must remain local; never send them or invent a response.

## 4. Run, snapshot, and replay integrity

- Create **one sealed snapshot for each consumed batch** at `artifacts/runs/<run-id>/batches/<batch-id>.json`, conforming to `snapshot.schema.json` and `schema_version: travel-claim-snapshot/2`.
- Preserve claim and independent trip/permit revisions, line findings and source IDs, decisions and request relationships, cancellations, financial state, and owned issues, with their required schema references.
- Keep Finance `admitted_event_ids` distinct from cancellation activity references. Every `issue_record_ids` entry must resolve to an `issues[].record_id`.
- The first snapshot has `predecessor: null`. Every later snapshot's `predecessor` refers to the prior retained snapshot by **relative path and SHA-256**.
- Each snapshot's `source_binding` refers to the run's `sources.json` by **relative path and SHA-256**. No file hashes itself.
- Preserve sealed prior states when later batches change the current view. Never silently overwrite a prior snapshot or change its predecessor binding.
- Unchanged replay must preserve obligation/event identities and monetary results, without duplicating payment effects.
- If recomputation would change sealed content, create a **new run** linked to the prior one and explain the divergence instead of overwriting the old run.
- Detect and clearly report missing or corrupt prior state. Recovery may reconstruct state only from complete retained source/event history; it must not invent past execution times.
- Keep source, batch, snapshot, CSV, report, and queue references mutually consistent on first run, retry, partial result, and replay.

## 5. Required repository artifacts

Paths below are relative to the repository. Replace angle-bracketed placeholders with stable nonempty IDs. Required JSON is UTF-8.

| Path | Contract |
| --- | --- |
| `skills/travel-expense-claim/SKILL.md` | Reusable Skill with name/description metadata, inputs, invocation instructions, human/side-effect boundaries, outputs, errors/retries, and links to its supporting files. |
| Supporting Skill files | Implementation, checks, and focused references under the Skill or clearly documented project paths; no hard-coded answers to the supplied cases. |
| `README.md` | Prerequisites, additional setup, exact batch and replay commands, success/partial/failure behavior, verification commands, recovery, and operational handoff. |
| `interviews/*.md` | **Original, complete Work Sim Markdown export for every session**, including metadata and all participant-visible messages. One final complete export per session; do not rewrite or summarize. |
| `artifacts/runs/<run-id>/sources.json` | Manifest binding source observations to retained content and identifying unavailable scope. Exact fields are specified below. |
| `artifacts/runs/<run-id>/batches/<batch-id>.json` | Immutable, schema-conformant snapshot for each consumed batch. |
| `artifacts/runs/<run-id>/claims.csv` | Exactly one current row per claim with the specified column names and correct monetary treatment. |
| `artifacts/runs/<run-id>/report.md` | Operations-facing handoff of completed work, unresolved amounts and obligations, blockers, owners, next evidence/actions, provenance, and significant batch/queue changes. Cover cancellations without claims, without inventing claim rows. |
| Coding-session evidence | **Actual** supported capture-session and checkpoint records corresponding to the submitted code revision; self-written substitutes do not count. |

### `sources.json` contract

At minimum, include top-level `run_id`, `source_version`, `case_clock`, and `files`. Cover **all five native URLs**.

For every retained piece or unavailable portion, record:

- `source_id` (unique when a source is split into multiple pieces)
- `path` (relative retained-content path, or `null` if unavailable)
- `sha256` (observed hash of retained bytes, or `null` if unavailable)
- `status` (`read` or `unavailable`)
- `error` (nullable)
- `url` (native source URL)
- `locator` (specific page, tab, section, or other relevant location)
- `observed_at` (actual UTC observation time)
- `version` (observed source version, or `null` if unobtainable)

Represent usable partial reads and unavailable portions separately; explain missing scope and its impact. Never assert complete access based solely on a successful access attempt.

### `claims.csv` contract

The exact header order is:

```csv
claim_id,revision,trip_id,status,allowed_cents,paid_cents,balance_cents,next_owner,reason
```

Produce one **current** row per claim. Do not add synthetic claim rows for independent trip/permit cancellations.

### `report.md` usability requirement

An operations reader must be able to tell which cases are complete, which monetary amounts are paid/outstanding/unknown, what remains unresolved, which person or role acts next, what evidence they need, and how the conclusion is supported. Explain significant changes between batches and point to repair queue views where appropriate. A partial run must not be presented as complete.

## 6. Verification and failure behavior

Verify against the **actual supplied record set and all arrival batches**; additional synthetic fixtures may supplement but not substitute for the primary run.

- Exercise the ordinary connected path and every material branch: incomplete claims, decisions/returns, partial responses, monetary review and reconciliation, corrections, independent cancellations with and without claims, replay, and recovery.
- Assert identities, quantities, integer-cent arithmetic, line/source bindings, decision/request and issue references, state transitions, and expected revalidation—not just status labels or schema validity.
- Validate every snapshot against the public schema and independently verify predecessor and `source_binding` hashes, retained content, output consistency, and replay invariants.
- Inspect the **actual** report, claims CSV, queue/views, and sealed snapshots. Confirm operational clarity, not just automated test passes.
- Make success, partial, and failure outcomes explicit; preserve truthful diagnostics and the work/evidence needed for retry. Document unrun tests, inaccessible material, and implementation limitations.
- No case-count cap or arbitrary time limit excuses omission of assigned records or branches.

## 7. Reproducibility and submission

- Start from the [public travel-expense-claim template](https://github.com/GitRollTraining/travel-expense-claim). Preserve and use its `README.md` and `snapshot.schema.json` as applicable. Use Git, an AI coding agent, and the program's supported coding-session capture.
- Document the chosen implementation language, dependencies, any source-access configuration, and exact run/replay/recovery commands. No real employee identity, bank information, or paid data source is required.
- Commit and push the original interview exports together with the submitted code revision; ensure the facilitator can access them. If an original export is unavailable, contact the facilitator rather than reconstructing it.
- Confirm that real coding-session capture/checkpoint evidence exists for the submitted revision. Provide the exact commit, run ID, output locations, and capture references in the handoff.

## 8. Business facts to confirm from the interview and sources

Do not settle these from guesses or implementation convenience:

- All five native URLs, their sections/tabs, availability and completeness.
- Case clock, arrival-batch order, and date/time interpretation.
- Meaning of permission, trip, permit, claim, line, review, approval, cancellation, payment, balance, and closure states.
- Monetary rules, identities/matching keys, tolerances, and rounding where applicable.
- Who may issue, accept, reverse, or amend human decisions and what evidence makes a scenario decision authorized.
- How missing evidence, corrections, returned work, and cancellations affect dependent versus independent work.
- Any genuine contradiction or missing rule, with an identified person to resolve it.

Record the source-grounded business rules after the interview; distinguish confirmed facts from unresolved questions. This section is **not permission to invent or freeze policy before evidence exists**.

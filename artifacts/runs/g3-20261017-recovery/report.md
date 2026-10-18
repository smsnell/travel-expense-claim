# Operations handoff — g3-20261017-recovery / batch 4

Source mode: **offline-recovery**. Retained inputs from `g3-20261017`; no fresh native access claimed. Inspect [recomputation comparison](comparison.json) and [prior run link](prior-run.json) for divergence.

Coverage: all-source-batches. Case clock: 2026-11-15, Europe/Amsterdam; event times UTC.

## Financial exposure

| Category | Amount / count | Meaning |
| --- | ---: | --- |
| Actually payable now | EUR 0.00 | Current supported entitlement, valid existing approvals, no release blocker |
| Known held entitlements (gross) | EUR 1280.01 | Reviewed amounts awaiting authority or other resolution; not authorized for payment |
| Unknown held claim totals | 10 claims | Amount unknown, not zero |
| Supported lines within unknown totals | EUR 60.00 | Partial evidence retained; does not establish aggregate entitlement or permit partial payment |
| Unreconciled confirmed transfers | EUR 100.00 | Money remains on original obligations pending Finance disposition; cannot offset replacement costs |
| Unsettled accepted Finance commitments | EUR 0.00 | Existing commitments only; zero does not mean zero unresolved exposure |

These categories overlap and must not be added as a single balance. Gross held entitlement is not reduced by money attached to a different obligation. Confirmed net paid across claims: EUR 12034.15.

Payable means supported current entitlement with valid human approvals and no blocking issue. A held amount is not authorized for release. Accepted original Finance commitments remain visible independently of changed eligibility. These are local workflow results; no requests were sent and no money moved.

## Payment actions

| Claim | Payable EUR | Held entitlement EUR | Net paid EUR | Balance EUR | Owner | Next action |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| C119 | 0.00 | 1000.01 | 0.00 | unknown | Administration / authorized reviewers | Obtain valid current C119 r1 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. |
| C18 | 0.00 | 100.00 | 100.00 | unknown | Administration / authorized reviewers | Obtain valid current C18 r2 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision.; Resolve REQ-C18 against current entitlement and its original trip/cost basis; reconcile any linked refund/late transfer. A matching total alone is insufficient.; Confirm original financial disposition and current trip authority before releasing a replacement request. |
| C21 | 0.00 | 80.00 | 0.00 | unknown | EMP-01 / LEAD-01 | Obtain funding decision. |
| C26 | 0.00 | 100.00 | 0.00 | unknown | Administration / authorized reviewers | Obtain valid current C26 r1 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. |

## Blockers and supported partial evidence

| Subject / revision | Supported line evidence EUR | Claim entitlement EUR | Blocker | Owner | Specific next action |
| --- | ---: | ---: | --- | --- | --- |
| C08 r1 | 0.00 | unknown | COST-08: merchant_payment_missing_or_ambiguous | EMP-01 / Administration | Provide one settled merchant transaction matching C08 r1, COST-08, EMP-01, T08 r1, receipt R-COST-08, 120.00 EUR, and its paid date; a receipt alone is insufficient. |
| C10 r1 | 0.00 | unknown | COST-10: late_permit | Finance | Obtain a Finance exception explicitly covering late_permit for C10 r1, COST-10, EMP-01, T10 r1; preserve the original arrangement-authority breach and obtain current claim reviews. |
| C112 r1 | 0.00 | unknown | COST-112-1: late_filing | Finance | Obtain a Finance exception explicitly covering late_filing for C112 r1, COST-112-1, EMP-03, T112 r1, with allowed original amount and reason; otherwise retain the hold. |
| C113 r1 | 0.00 | unknown | COST-113-1: filed_before_employee_payment | EMP-03 / Administration | Clarify first filing 2026-09-01 for C113 r1, COST-113-1, EMP-03, T113 r1 against the later settled merchant paid date; provide corrected source evidence without silently changing the original filing. |
| C114 r1 | 20.00 | unknown | COST-114-2: merchant_payment_missing_or_ambiguous | EMP-03 / Administration | Provide one settled merchant transaction matching C114 r1, COST-114-2, EMP-03, T114 r1, receipt R-COST-114-2, 15.00 EUR, and its paid date; a receipt alone is insufficient. |
| C116 r1 | 0.00 | unknown | COST-116-1: cap_missing_or_ambiguous | Finance | Finance must supply the category cap in USD applicable in NL on the employee-payment date for C116 r1, COST-116-1, EMP-03, T116 r1; include units and effective dates. |
| C116 r1 | 0.00 | unknown | COST-116-2: fx_missing_or_ambiguous | Finance | Finance must supply the exact employee-payment-date EUR-per-GBP rate for C116 r1, COST-116-2, EMP-03, T116 r1; retain its effective date and reference. |
| C117 r1 | 40.00 | unknown | COST-117-1: category_unknown | Finance | Administration/Finance must classify the actual purchase for C117 r1, COST-117-1, EMP-03, T117 r1 using authoritative category evidence; do not assume zero entitlement. |
| C119 r1 | 1000.01 | 1000.01 | missing director response | Administration / authorized reviewers | Obtain valid current C119 r1 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. |
| C18 r2 | 100.00 | 100.00 | missing administration response | Administration / authorized reviewers | Obtain valid current C18 r2 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. |
| C18 r2 | 100.00 | 100.00 | Original obligation requires explicit Finance reconciliation/resolution | Finance | Resolve REQ-C18 against current entitlement and its original trip/cost basis; reconcile any linked refund/late transfer. A matching total alone is insufficient. |
| C18 r2 | 100.00 | 100.00 | REQ-C18 belongs to prior T18 r1; transfers cannot be assigned to replacement costs | Finance / Administration | Confirm original financial disposition and current trip authority before releasing a replacement request. |
| C21 r1 | 80.00 | 80.00 | Budget owner requests a funding review before committing. | EMP-01 / LEAD-01 | Obtain funding decision. |
| C22 r1 | 0.00 | unknown | COST-22: fx_missing_or_ambiguous | Finance | Finance must supply the exact employee-payment-date EUR-per-GBP rate for C22 r1, COST-22, EMP-01, T22 r1; retain its effective date and reference. |
| C23 r1 | 0.00 | unknown | COST-23: cap_missing_or_ambiguous | Finance | Finance must supply the category cap in EUR applicable in BE on the employee-payment date for C23 r1, COST-23, EMP-01, T23 r1; include units and effective dates. |
| C25 r1 | 0.00 | unknown | COST-25: permit_unapproved | Finance | Supply valid permit authority for C25 r1, COST-25, EMP-01, T25 r1, or a Finance exception explicitly covering permit_unapproved for reimbursement only; do not retroactively approve arrangements. |
| C26 r1 | 100.00 | 100.00 | missing administration response | Administration / authorized reviewers | Obtain valid current C26 r1 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. |

Supported line evidence is retained work, not permission to pay a partial incomplete claim. See the [fact-level repair queue](repair-queue.md) for source locators and stable issue IDs. Unknown CSV money is blank; known zero is 0.

## Independent cancellations

| Process | Target | Business state | Financial consequence | Claims / original requests | Owner |
| --- | --- | --- | --- | --- | --- |
| TC122 | trip T122 | confirmed | no-financial-effect | None | None |
| TC121 | permit P121 | confirmed | resolved | C121, REQ-C121 | None |
| TC018 | trip T18 | confirmed | unresolved | C18, REQ-C18 | Finance / Administration |
| TC019 | trip T19 | confirmed | resolved | C19, REQ-C19 | None |

Cancellation confirmation must strictly follow initiation, effective at confirmation. Business cancellation does not itself cancel a Finance request or release a commitment. Permit cancellation leaves the trip active; trip cancellation retires that exact trip version and its linked permit.

## Completed work and full register

107 of 121 current claims have a completed state; 14 remain unresolved. The [full CSV](claims.csv) contains exactly one current row per claim; [sealed snapshots](batches/) retain line, permission, decision and Finance evidence. Reimbursed closure requires current approvals, supported entitlement, reconciled transfers/refunds, required Finance resolutions and no outstanding issue or financial obligation. A zero balance alone never closes a case.

## Budget and changes

Consulting / Client-A / 2026: allocation EUR 20000.00, net settled EUR 14034.15, remaining commitments EUR 3000.00, available EUR 2965.85. Prior obligations are included; settled portions are not subtracted twice. Funds do not replace budget approval.
- [Batch 1](batches/1.json): 120 claims; 100 admitted Finance IDs; 18 open fact items. Added 18; removed from current queue 0 (see retained prior snapshot and issue history).
- [Batch 2](batches/2.json): 120 claims; 200 admitted Finance IDs; 27 open fact items. Added 10; removed from current queue 1 (see retained prior snapshot and issue history).
- [Batch 3](batches/3.json): 121 claims; 210 admitted Finance IDs; 24 open fact items. Added 7; removed from current queue 10 (see retained prior snapshot and issue history).
- [Batch 4](batches/4.json): 121 claims; 219 admitted Finance IDs; 18 open fact items. Added 0; removed from current queue 6 (see retained prior snapshot and issue history).

## Provenance and remaining scope

All native source observations and exact retained bytes are bound by [sources.json](sources.json). Native Notion access is unavailable; the explicitly supplied manual policy has unknown export time and unverified live equivalence. Retained-input replay is labelled offline and never described as fresh access. Same-batch simultaneous review arrivals remain subject to exact actor, role, subject, revision and packet checks; no deliberation order is invented.

Coverage and deferred records: [coverage.json](coverage.json). Unresolved cases are owned operational outcomes; G3 final owner review and handoff acceptance pending


Revision and issue history is retained in snapshot `claim_history`, `revision_history`, `decision_history`, and `repair_history`. Corrections revalidate affected authority even at unchanged totals; a carried missing fact stays open until its specific evidence arrives. Local drafts did not cause the supplied scenario responses.


`closed-reimbursed` records that existing source-backed human approvals, entitlement and Finance facts satisfy the accepted closure conditions. The Skill validates and reports that evidence; it grants no approval, exception or payment authority.

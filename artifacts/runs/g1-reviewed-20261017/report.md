# Operations handoff — g1-reviewed-20261017 / batch 2

Coverage: partial-G1. Case clock: 2026-11-15, Europe/Amsterdam; event times UTC.

**Payable now: EUR 105.00. Known held payment balances: EUR 200.00.** 13 held entitlement totals remain unknown; these are not zero. Confirmed net paid: EUR 11539.15.

Payable means supported current entitlement with valid human approvals and no blocking issue. A held amount is not authorized for release. Accepted original Finance commitments remain visible independently of changed eligibility. These are local workflow results; no requests were sent and no money moved.

## Payment actions

| Claim | Payable EUR | Known held EUR | Net paid EUR | Balance EUR | Owner | Next action |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| C16 | 60.00 | 0.00 | 40.00 | 60.00 | Finance | Finance: confirm settlement against the existing obligation; do not duplicate its request. |
| C120 | 45.00 | 0.00 | 30.00 | 45.00 | Finance | Finance: confirm settlement against the existing obligation; do not duplicate its request. |
| C17 | 0.00 | 100.00 | 0.00 | 100.00 | Finance | Supply explicit retry authorization before a new attempt. |
| C18 | 0.00 | 100.00 | 0.00 | unknown | Finance | Confirm original request status/cancellation; hold competing replacements.; Resolve cancellation-dependent eligibility/review; keep original Finance obligation and payment history. |
| C20 | 0.00 | 0.00 | 110.00 | -10.00 | Finance | Reconcile linked confirmed refund and explicit resolution; matching a later total alone is insufficient. |

## Blockers and supported partial evidence

| Subject / revision | Supported line evidence EUR | Claim entitlement EUR | Blocker | Owner | Specific next action |
| --- | ---: | ---: | --- | --- | --- |
| C08 r1 | 0.00 | unknown | COST-08: merchant_payment_missing_or_ambiguous | EMP-01 / Administration | Provide one settled merchant transaction matching C08 r1, COST-08, EMP-01, T08 r1, receipt R-COST-08, 120.00 EUR, and its paid date; a receipt alone is insufficient. |
| C09 r1 | 80.00 | 80.00 | Please supply the revised trip evidence. | EMP-01 / LEAD-01 | Provide revised trip evidence. |
| C10 r1 | 0.00 | unknown | COST-10: late_permit | Finance | Obtain a Finance exception explicitly covering late_permit for C10 r1, COST-10, EMP-01, T10 r1; preserve the original arrangement-authority breach and obtain current claim reviews. |
| C112 r1 | 0.00 | unknown | COST-112-1: late_filing | Finance | Obtain a Finance exception explicitly covering late_filing for C112 r1, COST-112-1, EMP-03, T112 r1, with allowed original amount and reason; otherwise retain the hold. |
| C113 r1 | 0.00 | unknown | COST-113-1: filed_before_employee_payment | EMP-03 / Administration | Clarify first filing 2026-09-01 for C113 r1, COST-113-1, EMP-03, T113 r1 against the later settled merchant paid date; provide corrected source evidence without silently changing the original filing. |
| C114 r1 | 20.00 | unknown | COST-114-2: merchant_payment_missing_or_ambiguous | EMP-03 / Administration | Provide one settled merchant transaction matching C114 r1, COST-114-2, EMP-03, T114 r1, receipt R-COST-114-2, 15.00 EUR, and its paid date; a receipt alone is insufficient. |
| C116 r1 | 0.00 | unknown | COST-116-1: cap_missing_or_ambiguous | Finance | Finance must supply the category cap in USD applicable in NL on the employee-payment date for C116 r1, COST-116-1, EMP-03, T116 r1; include units and effective dates. |
| C116 r1 | 0.00 | unknown | COST-116-2: fx_missing_or_ambiguous | Finance | Finance must supply the exact employee-payment-date EUR-per-GBP rate for C116 r1, COST-116-2, EMP-03, T116 r1; retain its effective date and reference. |
| C117 r1 | 40.00 | unknown | COST-117-1: category_unknown | Finance | Administration/Finance must classify the actual purchase for C117 r1, COST-117-1, EMP-03, T117 r1 using authoritative category evidence; do not assume zero entitlement. |
| C119 r1 | 1000.01 | 1000.01 | missing director response | Administration / authorized reviewers | Obtain valid current subject/revision responses; do not infer approval. |
| C12 r1 | 0.00 | unknown | COST-12: late_filing | Finance | Obtain a Finance exception explicitly covering late_filing for C12 r1, COST-12, EMP-01, T12 r1, with allowed original amount and reason; otherwise retain the hold. |
| C121 r1 | 30.00 | unknown | Cancellation confirmed; original purchase evidence retained | Finance / Administration | Resolve cancellation-dependent eligibility/review; keep original Finance obligation and payment history. |
| C17 r1 | 100.00 | 100.00 | Finance attempt failed; no transfer effect | Finance | Supply explicit retry authorization before a new attempt. |
| C18 r1 | 100.00 | unknown | Finance cancellation requested, not confirmed | Finance | Confirm original request status/cancellation; hold competing replacements. |
| C18 r1 | 100.00 | unknown | Cancellation confirmed; original purchase evidence retained | Finance / Administration | Resolve cancellation-dependent eligibility/review; keep original Finance obligation and payment history. |
| C20 r1 | 100.00 | 100.00 | Confirmed transfers exceed the current reviewed obligation | Finance | Reconcile linked confirmed refund and explicit resolution; matching a later total alone is insufficient. |
| C21 r1 | 80.00 | 80.00 | Budget owner requests a funding review before committing. | EMP-01 / LEAD-01 | Obtain funding decision. |
| C22 r1 | 0.00 | unknown | COST-22: fx_missing_or_ambiguous | Finance | Finance must supply the exact employee-payment-date EUR-per-GBP rate for C22 r1, COST-22, EMP-01, T22 r1; retain its effective date and reference. |
| C23 r1 | 0.00 | unknown | COST-23: cap_missing_or_ambiguous | Finance | Finance must supply the category cap in EUR applicable in BE on the employee-payment date for C23 r1, COST-23, EMP-01, T23 r1; include units and effective dates. |
| C25 r1 | 0.00 | unknown | COST-25: permit_unapproved | Finance | Supply valid permit authority for C25 r1, COST-25, EMP-01, T25 r1, or a Finance exception explicitly covering permit_unapproved for reimbursement only; do not retroactively approve arrangements. |
| C26 r1 | 100.00 | 100.00 | missing administration response | Administration / authorized reviewers | Obtain valid current subject/revision responses; do not infer approval. |

Supported line evidence is retained work, not permission to pay a partial incomplete claim. See the [fact-level repair queue](repair-queue.md) for source locators and stable issue IDs. Unknown CSV money is blank; known zero is 0.

## Independent cancellations

| Process | Target | Business state | Financial consequence | Claims / original requests | Owner |
| --- | --- | --- | --- | --- | --- |
| TC122 | trip T122 | confirmed | no-financial-effect | None | None |
| TC121 | permit P121 | confirmed | unresolved | C121 | Finance / Administration |
| TC018 | trip T18 | confirmed | unresolved | C18, REQ-C18 | Finance / Administration |

Cancellation confirmation must strictly follow initiation, effective at confirmation. Business cancellation does not itself cancel a Finance request or release a commitment. Permit cancellation leaves the trip active; trip cancellation retires that exact trip version and its linked permit.

## Completed work and full register

99 of 120 current claims have a completed state; 21 remain unresolved. The [full CSV](claims.csv) contains exactly one current row per claim; [sealed snapshots](batches/) retain line, permission, decision and Finance evidence. Reimbursed closure requires current approvals, supported entitlement, reconciled transfers/refunds, required Finance resolutions and no outstanding issue or financial obligation. A zero balance alone never closes a case.

## Budget and changes

Consulting / Client-A / 2026: allocation EUR 20000.00, net settled EUR 13539.15, remaining commitments EUR 3305.00, available EUR 3155.85. Prior obligations are included; settled portions are not subtracted twice. Funds do not replace budget approval.
- [Batch 1](batches/1.json): 120 claims; 100 admitted Finance IDs; 18 open fact items. Added 18; removed from current queue 0 (see retained prior snapshot and issue history).
- [Batch 2](batches/2.json): 120 claims; 200 admitted Finance IDs; 23 open fact items. Added 5; removed from current queue 0 (see retained prior snapshot and issue history).

## Provenance and remaining scope

All native source observations and exact retained bytes are bound by [sources.json](sources.json). Native Notion access is unavailable; the explicitly supplied manual policy has unknown export time and unverified live equivalence. Retained-input replay is labelled offline and never described as fresh access. Same-batch simultaneous review arrivals remain subject to exact actor, role, subject, revision and packet checks; no deliberation order is invented.

Coverage and deferred records: [coverage.json](coverage.json). G2 corrections/partial-response history, remaining cancellations/Finance branches and replay/recovery not implemented

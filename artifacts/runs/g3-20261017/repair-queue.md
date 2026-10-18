# Local repair queue — g3-20261017 / batch 4

Grouped by subject/revision; each row is one independent missing fact. Local only; no requests sent. Later supplied scenario evidence is not a reply caused by these drafts.

| Subject/revision | Fact ID | Blocker | Owner | Evidence/action needed | Source |
| --- | --- | --- | --- | --- | --- |
| C08 r1 | C08:r1:COST-08:merchant_payment_missing_or_ambiguous | COST-08: merchant_payment_missing_or_ambiguous | EMP-01 / Administration | Provide one settled merchant transaction matching C08 r1, COST-08, EMP-01, T08 r1, receipt R-COST-08, 120.00 EUR, and its paid date; a receipt alone is insufficient. | initial: page 8, card 1, receipts: page 4, card 2 |
| C10 r1 | C10:r1:COST-10:late_permit | COST-10: late_permit | Finance | Obtain a Finance exception explicitly covering late_permit for C10 r1, COST-10, EMP-01, T10 r1; preserve the original arrangement-authority breach and obtain current claim reviews. | initial: page 10, card 1, receipts: page 5, card 2, registers: Merchant payments!A14:I14 |
| C112 r1 | C112:r1:COST-112-1:late_filing | COST-112-1: late_filing | Finance | Obtain a Finance exception explicitly covering late_filing for C112 r1, COST-112-1, EMP-03, T112 r1, with allowed original amount and reason; otherwise retain the hold. | initial: page 111, card 1, receipts: page 94, card 2, registers: Merchant payments!A192:I192 |
| C113 r1 | C113:r1:COST-113-1:filed_before_employee_payment | COST-113-1: filed_before_employee_payment | EMP-03 / Administration | Clarify first filing 2026-09-01 for C113 r1, COST-113-1, EMP-03, T113 r1 against the later settled merchant paid date; provide corrected source evidence without silently changing the original filing. | initial: page 112, card 1, receipts: page 95, card 1, registers: Merchant payments!A193:I193 |
| C114 r1 | C114:r1:COST-114-2:merchant_payment_missing_or_ambiguous | COST-114-2: merchant_payment_missing_or_ambiguous | EMP-03 / Administration | Provide one settled merchant transaction matching C114 r1, COST-114-2, EMP-03, T114 r1, receipt R-COST-114-2, 15.00 EUR, and its paid date; a receipt alone is insufficient. | initial: page 113, card 1, receipts: page 96, card 1 |
| C116 r1 | C116:r1:COST-116-1:cap_missing_or_ambiguous | COST-116-1: cap_missing_or_ambiguous | Finance | Finance must supply the category cap in USD applicable in NL on the employee-payment date for C116 r1, COST-116-1, EMP-03, T116 r1; include units and effective dates. | initial: page 115, card 1, receipts: page 97, card 2, registers: Merchant payments!A197:I197, registers: FX!A7:D7 |
| C116 r1 | C116:r1:COST-116-2:fx_missing_or_ambiguous | COST-116-2: fx_missing_or_ambiguous | Finance | Finance must supply the exact employee-payment-date EUR-per-GBP rate for C116 r1, COST-116-2, EMP-03, T116 r1; retain its effective date and reference. | initial: page 115, card 1, receipts: page 98, card 1, registers: Merchant payments!A198:I198 |
| C117 r1 | C117:r1:COST-117-1:category_unknown | COST-117-1: category_unknown | Finance | Administration/Finance must classify the actual purchase for C117 r1, COST-117-1, EMP-03, T117 r1 using authoritative category evidence; do not assume zero entitlement. | initial: page 116, card 1, receipts: page 98, card 2, registers: Merchant payments!A199:I199 |
| C119 r1 | C119:r1:review_authority | missing director response | Administration / authorized reviewers | Obtain valid current C119 r1 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. | initial: page 118, card 1 |
| C18 r2 | C18:r2:finance_resolution:REQ-C18 | Original obligation requires explicit Finance reconciliation/resolution | Finance | Resolve REQ-C18 against current entitlement and its original trip/cost basis; reconcile any linked refund/late transfer. A matching total alone is insufficient. | registers: Finance activity!A43:M43, registers: Finance activity!A19:M19, registers: Finance activity!A20:M20, registers: Finance activity!A21:M21 |
| C18 r2 | C18:r2:prior_request_basis:REQ-C18 | REQ-C18 belongs to prior T18 r1; transfers cannot be assigned to replacement costs | Finance / Administration | Confirm original financial disposition and current trip authority before releasing a replacement request. | registers: Finance activity!A43:M43, registers: Finance activity!A19:M19, registers: Finance activity!A20:M20, registers: Finance activity!A21:M21 |
| C18 r2 | C18:r2:review_authority | missing administration response | Administration / authorized reviewers | Obtain valid current C18 r2 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. | updates: page 4, card 1 |
| C21 r1 | C21:r1:review_return | Budget owner requests a funding review before committing. | EMP-01 / LEAD-01 | Obtain funding decision. | registers: Review ledger!A57:M57 |
| C22 r1 | C22:r1:COST-22:fx_missing_or_ambiguous | COST-22: fx_missing_or_ambiguous | Finance | Finance must supply the exact employee-payment-date EUR-per-GBP rate for C22 r1, COST-22, EMP-01, T22 r1; retain its effective date and reference. | initial: page 22, card 1, receipts: page 11, card 2, registers: Merchant payments!A26:I26 |
| C23 r1 | C23:r1:COST-23:cap_missing_or_ambiguous | COST-23: cap_missing_or_ambiguous | Finance | Finance must supply the category cap in EUR applicable in BE on the employee-payment date for C23 r1, COST-23, EMP-01, T23 r1; include units and effective dates. | initial: page 23, card 1, receipts: page 12, card 1, registers: Merchant payments!A27:I27 |
| C25 r1 | C25:r1:COST-25:permit_unapproved | COST-25: permit_unapproved | Finance | Supply valid permit authority for C25 r1, COST-25, EMP-01, T25 r1, or a Finance exception explicitly covering permit_unapproved for reimbursement only; do not retroactively approve arrangements. | initial: page 24, card 1, receipts: page 14, card 1, registers: Merchant payments!A31:I31 |
| C26 r1 | C26:r1:review_authority | missing administration response | Administration / authorized reviewers | Obtain valid current C26 r1 responses for the listed missing/invalid roles and complete packet context; prior revisions cannot authorize this revision. | initial: page 25, card 1 |
| TC018 r1 | TC018:r1:financial_disposition | Cancellation has costs or obligations; business confirmation alone does not resolve them | Finance / Administration | Review linked claims, original requests, scoped cancellation disposition and current packet context; obtain required Finance resolution after prior acceptance. | registers: Travel cancellations!A10:N10, registers: Travel cancellations!A11:N11 |

## Fact history

| Batch | Action | Fact | Prior fact | Evidence / reason |
| --- | --- | --- | --- | --- |
| 1 | opened | C08:r1:COST-08:merchant_payment_missing_or_ambiguous |  | COST-08: merchant_payment_missing_or_ambiguous; Finance:  |
| 1 | opened | C09:r1:review_return |  | Please supply the revised trip evidence.; Finance:  |
| 1 | opened | C10:r1:COST-10:late_permit |  | COST-10: late_permit; Finance:  |
| 1 | opened | C112:r1:COST-112-1:late_filing |  | COST-112-1: late_filing; Finance:  |
| 1 | opened | C113:r1:COST-113-1:filed_before_employee_payment |  | COST-113-1: filed_before_employee_payment; Finance:  |
| 1 | opened | C114:r1:COST-114-2:merchant_payment_missing_or_ambiguous |  | COST-114-2: merchant_payment_missing_or_ambiguous; Finance:  |
| 1 | opened | C116:r1:COST-116-1:cap_missing_or_ambiguous |  | COST-116-1: cap_missing_or_ambiguous; Finance:  |
| 1 | opened | C116:r1:COST-116-2:fx_missing_or_ambiguous |  | COST-116-2: fx_missing_or_ambiguous; Finance:  |
| 1 | opened | C117:r1:COST-117-1:category_unknown |  | COST-117-1: category_unknown; Finance:  |
| 1 | opened | C119:r1:review_authority |  | missing director response; Finance:  |
| 1 | opened | C12:r1:COST-12:late_filing |  | COST-12: late_filing; Finance:  |
| 1 | opened | C121:r1:travel_cancellation:TC121 |  | Cancellation requested; readiness paused, not confirmed; Finance:  |
| 1 | opened | C21:r1:review_return |  | Budget owner requests a funding review before committing.; Finance:  |
| 1 | opened | C22:r1:COST-22:fx_missing_or_ambiguous |  | COST-22: fx_missing_or_ambiguous; Finance:  |
| 1 | opened | C23:r1:COST-23:cap_missing_or_ambiguous |  | COST-23: cap_missing_or_ambiguous; Finance:  |
| 1 | opened | C25:r1:COST-25:permit_unapproved |  | COST-25: permit_unapproved; Finance:  |
| 1 | opened | C26:r1:review_authority |  | missing administration response; Finance:  |
| 1 | opened | TC121:r1:financial_disposition |  | Cancellation has costs or obligations; business confirmation alone does not resolve them; Finance:  |
| 2 | opened | C121:r1:COST-121:travel_cancellation |  | COST-121: travel_cancellation; Finance:  |
| 2 | opened | C121:r1:review_authority |  | D-C121-1-claim-administration-1: packet cancellation context mismatch, review reply predates cancellation context; D-C121-1-claim-budget_owner-1: packet cancellation context mismatch, review reply predates cancellation context; D-C121-1-claim-supervisor-1: packet cancellation context mismatch, review reply predates cancellation context; missing administration response; Finance:  |
| 2 | opened | C18:r1:COST-18:travel_cancellation |  | COST-18: travel_cancellation; Finance:  |
| 2 | opened | C18:r1:review_authority |  | D-C18-1-claim-administration-1: packet cancellation context mismatch, review reply predates cancellation context; D-C18-1-claim-budget_owner-1: packet cancellation context mismatch, review reply predates cancellation context; D-C18-1-claim-supervisor-1: packet cancellation context mismatch, review reply predates cancellation context; missing administration response; Finance:  |
| 2 | opened | C17:r1:finance_retry |  | Finance attempt failed; no transfer effect; Finance:  |
| 2 | opened | C18:r1:finance_cancel |  | Finance cancellation requested, not confirmed; Finance:  |
| 2 | opened | C18:r1:finance_resolution:REQ-C18 |  | Original obligation requires explicit Finance reconciliation/resolution; Finance:  |
| 2 | opened | C20:r1:finance_resolution:REQ-C20 |  | Original obligation requires explicit Finance reconciliation/resolution; Finance:  |
| 2 | opened | C20:r1:overpayment |  | Confirmed net transfers exceed current supported entitlement; Finance:  |
| 2 | opened | TC018:r1:financial_disposition |  | Cancellation has costs or obligations; business confirmation alone does not resolve them; Finance:  |
| 2 | resolved | C121:r1:travel_cancellation:TC121 |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance:  |
| 3 | carried | C18:r2:review_authority | C18:r1:review_authority | Same missing fact remains unsupported on current revision; Finance:  |
| 3 | opened | C19:r2:COST-19:travel_cancellation |  | COST-19: travel_cancellation; Finance:  |
| 3 | opened | C19:r2:review_authority |  | D-C19-2-claim-administration-3: packet cancellation context mismatch, review reply predates cancellation context; D-C19-2-claim-budget_owner-3: packet cancellation context mismatch, review reply predates cancellation context; D-C19-2-claim-supervisor-3: packet cancellation context mismatch, review reply predates cancellation context; missing administration response; Finance:  |
| 3 | carried | C18:r2:finance_resolution:REQ-C18 | C18:r1:finance_resolution:REQ-C18 | Same missing fact remains unsupported on current revision; Finance:  |
| 3 | opened | C18:r2:prior_request_basis:REQ-C18 |  | REQ-C18 belongs to prior T18 r1; transfers cannot be assigned to replacement costs; Finance:  |
| 3 | opened | C19:r2:finance_resolution:REQ-C19 |  | Original obligation requires explicit Finance reconciliation/resolution; Finance:  |
| 3 | opened | TC019:r1:financial_disposition |  | Cancellation has costs or obligations; business confirmation alone does not resolve them; Finance:  |
| 3 | resolved | C09:r1:review_return |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C09-accepted |
| 3 | resolved | C12:r1:COST-12:late_filing |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C12-accepted |
| 3 | resolved | C121:r1:COST-121:travel_cancellation |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C121-accepted |
| 3 | resolved | C121:r1:review_authority |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C121-accepted |
| 3 | superseded | C18:r1:COST-18:travel_cancellation |  | Changed travel/cost basis supersedes the old issue; original missing evidence is not invented; Finance: F-C18-2 |
| 3 | resolved | C17:r1:finance_retry |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C17-2 |
| 3 | resolved | C18:r1:finance_cancel |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C18-2 |
| 3 | resolved | C20:r1:overpayment |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C20-2 |
| 4 | resolved | C19:r2:COST-19:travel_cancellation |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C19-3, F-C19-4 |
| 4 | resolved | C19:r2:review_authority |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C19-3, F-C19-4 |
| 4 | resolved | C19:r2:finance_resolution:REQ-C19 |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C19-3, F-C19-4 |
| 4 | resolved | C20:r1:finance_resolution:REQ-C20 |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance: F-C20-3 |
| 4 | resolved | TC121:r1:financial_disposition |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance:  |
| 4 | resolved | TC019:r1:financial_disposition |  | Specific supplied revision/review/Finance evidence removes this fact blocker; unrelated issues remain; Finance:  |

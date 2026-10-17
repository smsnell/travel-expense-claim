# G2 verification and inspection

All four supplied batches are processed in [g2-20261017](../../runs/g2-20261017/report.md), with fresh supported acquisition observations in [sources.json](../../runs/g2-20261017/sources.json). Four Drive sources are usable; native Notion returned 404. The explicitly supplied manual policy remains unverified against live Notion. Processing returns verified `partial`, exit 2; verification returns exit 0. G2 owner acceptance and G3 final handoff remain pending.

## Checks and actual outputs

- [49 passing tests](tests.txt): 3 source parsing/integrity, 10 original authority/money boundaries, 17 four-batch business/adversarial, 12 lifecycle and 7 output integrity checks. Command: `PYTHONDONTWRITEBYTECODE=1 PROJECT_D_TEST_G2_ALL_BATCHES=1 .venv/bin/python -m unittest discover -s tests -v`. Retained actual-source fixtures supplement the primary fresh run; synthetic mutations are labelled tests.
- [Primary verification](../../runs/g2-20261017/verification.json): four public-schema snapshots, byte hashes, predecessor/source references, identity/money invariants and exact CSV/report/queue consistency. [Coverage](../../runs/g2-20261017/coverage.json) accounts for all 127 claim revisions, 203 receipts, 307 review records/packets, 220 Finance deliveries and 9 cancellation deliveries. No deferred source records remain.
- [Unchanged replay](../../runs/g2-20261017-replay/comparison.json): four equivalent semantic states, stable requests/events, no repeated monetary effects. Run/binding identities and actual reconstruction timestamps intentionally differ.
- [Recovery demonstration](recovery-check.json): deliberately damaged only a temporary copy's fourth snapshot. Resume refused it; [recovery](../../runs/g2-20261017-recovery/report.md) used complete hash-verified retained sources. [Comparison with damaged state](../../runs/g2-20261017-recovery/comparison.json) truthfully reports the fourth comparison unavailable; the separate recovery check compares all four reconstructed states with the intact original and confirms equivalence. Temporary damaged copy was removed after the check; the original and reconstructed runs are retained. Tests additionally cover missing predecessors, corrupt source bytes/manifests, missing old implementation, interrupted view publication and unchanged retries.
- Original G1 runs, AGENTS.md, REQUIREMENTS.md, schema, original interviews and policy have no diff from the pushed milestone. Skill quick validation passes using system `python3`; the project runtime environment intentionally lacks the validator's PyYAML dependency, so its initial validation invocation failed before using the already-equipped system interpreter. No dependency was added.

## Decision evidence for owner inspection

| Accepted decision / branch | Source-based result | Code/check evidence |
| --- | --- | --- |
| D1 independent work | C114 retains supported COST-114-1 EUR20; COST-114-2 proof missing, aggregate unknown, no payment request | `workflow.py` line findings/owned issues; business test partial evidence; final CSV and snapshot |
| D2 partial fact repair | C19r2 amount disposition EUR80 retains cancellation/review/Finance issues. C19r3 scoped TC019 exception, fresh reviews, refund EUR20 and resolution close those facts; history remains | Batch 3/4 snapshots, repair history; business amount-only exception test |
| D3 current dependencies | C09 same EUR80 but new T09B/COST-09B requires new authority. C18 new T18B retains old REQ-C18/T18 payment EUR100 and Finance hold | Revision/decision/request history; unchanged-total and late-transfer business tests |
| D4 completion | C20 balance becomes zero in batch3 but stays held until batch4 Finance resolution. C19/C121 close on supported current facts. C114/C18 remain held | Batch 3/4 snapshots; refund/resolution and pre-acceptance-cancellation tests |
| Remaining money branches | C16/C120 instalments, C17 explicit retry, C24 excludes C03's already-paid EUR200 and pays only new EUR50, C05/C06 and C99–C109 threshold/rounding cases | Actual four-batch business tests and retained request/event records |
| Independent cancellations | TC122 trip cancelled with no claim; TC121 permit retired/trip active; TC018 retains unresolved Finance; TC019 resolved | Four cancellation records, strict ordering/actor/target adversarial tests |

Final current states: **103 closed-reimbursed, 2 closed-no-payment, 1 withdrawn, 1 rejected, 14 held**. Net confirmed paid EUR12,034.15. Eighteen owned repair facts remain; ten claim entitlement totals unknown. Report/queue/CSV were inspected: payment actions lead; C18's unreconciled transfer is visible despite unknown current balance; C114's partial evidence survives; each unresolved fact has an owner/action/source. Known reviewed entitlement awaiting approvals appears in the blocker table, distinct from an authorized payable balance. No temporary D4 owner labels remain in current outputs. The independent TC018 issue appears in the queue and cancellation section.

## Skill scan and manual review

Pinned local scanner 2.0.13, default local-only analyzers; no upload or LLM/cloud checks. Exact wrapper: `/home/mike/.codex/plugins/cache/fellowship-apprentice-workspace/apprentice-workspace/local/library/skills/scan-agent-skill/scripts/scan.sh skills/travel-expense-claim`. [Initial scan](security-scan-initial.md) exited 0 with three findings:

- MEDIUM, `scripts/workflow.py:364`, apparent `requests.get(` network primitive: accepted false positive. `requests` is the local request-state dictionary created by `reduce_batches`, passed into `_finance`; no HTTP client import or call exists.
- LOW, `scripts/__pycache__/source_io.cpython-314.pyc`: fixed by moving the generated, ignored bytecode directory outside the deliverable. Source files and sealed implementation digests are unchanged.
- INFO, `SKILL.md`, missing license metadata: retained. No owner-authorized license has been supplied; do not invent one.

[Final scan](security-scan.md) exits 0 after bytecode cleanup: zero high/critical/low findings, the same reviewed MEDIUM dictionary false positive, and INFO missing license. Manual review covers the Skill instructions, imports, paths, native URL constants, credentials/network absence and file writes. Runtime operates on local evidence/output files; its single unlink removes only a newly created invocation file before source acquisition in a new run, and writes are constrained to run paths. It sends no drafts, changes no native sources and moves no money. Scanner results are limited evidence, not certification.

G1 milestone `2bd09d3a69c1cc34a0219be0b197f164e07bfb07` is pushed to origin/main. G2 code/artifacts remain uncommitted for owner review. Owner manages supported coding-session capture verification.

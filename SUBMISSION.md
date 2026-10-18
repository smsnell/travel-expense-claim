# Project D submission — G3 accepted

Owner accepted all three gates and D1–D4, including **14 unresolved claims** and **unverified manual policy provenance**. This records acceptance outside sealed run evidence. Historical pending-review text in sealed outputs remains unchanged; acceptance does not imply full native-source verification.

## Deliverables

| Required deliverable | Submission path / evidence |
| --- | --- |
| Reusable Skill and supporting implementation | [SKILL.md](skills/travel-expense-claim/SKILL.md), its `scripts/`, [dependencies](requirements.txt), [tests](tests/) |
| Setup, invocation, partial/failure behavior, replay/recovery | [README.md](README.md), [source retrieval contract](SOURCE-RETRIEVAL.md) |
| Original complete interview | [interview-D-4.md](interviews/interview-D-4.md), unchanged; [earlier export archive/provenance](interviews/README.md) |
| Authoritative requirements and snapshot contract | [REQUIREMENTS.md](REQUIREMENTS.md), [snapshot.schema.json](snapshot.schema.json), [AGENTS.md](AGENTS.md) |
| Final source-bound run | **g3-20261017**: [sources](artifacts/runs/g3-20261017/sources.json), retained `inputs/`, [four sealed snapshots](artifacts/runs/g3-20261017/batches/), [coverage](artifacts/runs/g3-20261017/coverage.json) |
| Operations result | [report](artifacts/runs/g3-20261017/report.md), [claims CSV](artifacts/runs/g3-20261017/claims.csv), [owned repair queue/history](artifacts/runs/g3-20261017/repair-queue.md) |
| Accepted handoff / verification | [G3 handoff](artifacts/verification/g3-20261017/README.md), [56 integrated tests](artifacts/verification/g3-20261017/tests.txt), [independent inspection](artifacts/verification/g3-20261017/independent-handoff-review.md) |
| Reproducibility | [Replay comparison](artifacts/runs/g3-20261017-replay/comparison.json), [recovery evidence](artifacts/verification/g3-20261017/recovery-check.json), [exact code/source/C18 trace](artifacts/verification/g3-20261017/final-binding-and-C18.json) |
| Decisions/resources | [Design](DESIGN-PLAN.md), [tracker](PROJECT-TRACKER.md), preserved original forecasts and measured/unknown usage distinctions |
| Actual supported coding capture | Commit `Entire-Checkpoint` trailer and corresponding remote `refs/entire/checkpoints/<suffix>/<checkpoint-id>`; retrieval below. [Earlier code checkpoint evidence](artifacts/verification/g3-20261017/capture-and-token-evidence.json) remains historical. |

## Facilitator review: native Notion fallback

**Native Notion access returned404.** Owner-authorized [POL-2026.2.md](policy/POL-2026.2.md) is explicitly retained as manual input, with unknown export date and **unverified live equivalence/completeness**. No assertion of full native policy verification is made. Four Drive sources were freshly retrieved and their usable content/completeness checked. Future fresh runs must retry all five native locations; a restored policy requires comparison/rule review before reliance. This limitation is intentionally flagged for the facilitator, not silently waived by owner acceptance.

The result covers all four batches:121 claims/127 revisions,103 reimbursed closures, two zero-payment closures, one withdrawal, one rejection and14 held. Eighteen owned repair facts remain, including TC018 financial disposition. C18's EUR100 stays on its original obligation; `closed-reimbursed` reports valid existing human/source evidence and grants no approval authority. The report separates EUR1,280.01 gross held entitlements, ten unknown totals, EUR60 supported partial lines, EUR100 unreconciled transfers and EUR0 payable; these categories overlap.

## Revision and capture access

Repository: `https://github.com/smsnell/travel-expense-claim.git`. The final handoff identifies the exact submitted revision after push; from its checkout use `git rev-parse HEAD`. The G3 runtime scripts remain identical to implementation milestone `54cda8120dbb2cbe66a68702518eed7eff6d8634`; final submission changes package evidence/docs and the test fixture's interview path, not runtime logic.

Read the submitted commit's `Entire-Checkpoint` trailer with `git show -s --format=%B HEAD`. The checkpoint ref is `refs/entire/checkpoints/<last-two-ID-characters>/<ID>`. Fetch that exact advertised ref, for example:

```bash
git ls-remote origin refs/heads/main 'refs/entire/checkpoints/*'
git fetch origin refs/entire/checkpoints/N5/01M55TSTHMV18SHMSJFQH01PN5
git show FETCH_HEAD:0/metadata.json
```

The example identifies the preserved G2 code checkpoint; use the final submitted commit's trailer for its own checkpoint. Actual records include `metadata.json`, `0/metadata.json`, `0/full.jsonl`, `0/transcript.jsonl` and `0/content_hash.txt`, with task captures where supplied. Custom checkpoint refs are not fetched by every default clone. Remote main and checkpoint objects are fetched into an isolated verification repository after the final push, then inspected; repository permission for a separate facilitator account must be granted by the owner if needed. A self-written verification note is not a replacement transcript.

## Final review scope

Final diff review excludes virtual environments, bytecode, temporary download configurations/URLs, credentials, local capture scratch files and unrelated work. Original sealed run hashes are checked unchanged. D-4 and protected requirements/schema/instructions/policy are unchanged; historical interview paths resolve at preserved G2 history. G3 remains an explicitly limited source result even though the owner has accepted delivery. No further work is requested unless submission verification reveals a material issue.

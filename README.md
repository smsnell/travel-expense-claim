# Travel expense claim

Build a reusable Agent Skill for Alderbridge Consulting's travel reimbursement workflow.

## Start

1. Read the [full Project D task](https://private-pecorino-70e.notion.site/Travel-expense-claim-Task-and-submission-3da0b700541e81249039eff895f77c98) for the scope, workflow and deliverables.
2. Use **Use this template → Create a new repository** on [GitRollTraining/travel-expense-claim](https://github.com/GitRollTraining/travel-expense-claim), then clone your own repository and work there.

## Implementation and setup

Python 3.11+; supported Drive and Notion connectors for the invoking agent. The local Python runner has no connector credentials. Read [AGENTS.md](AGENTS.md), [REQUIREMENTS.md](REQUIREMENTS.md), [design](DESIGN-PLAN.md), and [tracker](PROJECT-TRACKER.md). The [Skill](skills/travel-expense-claim/SKILL.md) uses source validation, policy helpers, a batch reducer, output verification and a CLI; no database or hosted service.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The host needs venv/ensurepip. This workspace required owner-authorized official get-pip bootstrap into the project-local environment; nothing was installed system-wide. Direct dependencies are pinned. Each run records Python, dependency, script and schema versions in `implementation.json`.

## Fresh acquisition and invocation

The invoking agent attempts all five native sources and creates the handoff described in [SOURCE-RETRIEVAL.md](SOURCE-RETRIEVAL.md). Inspect usable content and completeness, retain exact returned bytes and actual observation times. The runner consumes that handoff; it does not authenticate remote origin or independently contact MCP. Hashes establish retained-byte integrity.

Use native Notion policy content by default. When unavailable, explicitly supply the owner-authorized file; the manifest preserves the failed native attempt and the backup's unknown export time/unverified live equivalence. Reviewed policy/sequence fingerprints fail closed on changed bytes until Operations and the maintainer review rule changes.

The actual four-batch G2 command was:

```bash
.venv/bin/python skills/travel-expense-claim/scripts/run.py run \
  --acquisition artifacts/acquisitions/g2-20261017/acquisition.json \
  --run-id g2-20261017 \
  --policy-file policy/POL-2026.2.md \
  --sequencing-file interviews/interview-D-4.md \
  --through-batch 4 \
  --prior-run artifacts/runs/g1-reviewed-20261017 \
  --change-reason "G2 four-batch corrections, cancellation and Finance reconciliation under accepted D4"
```

This records a historical acquisition. A new fresh run requires five new attempts and a new acquisition/run ID. Exact retries with unchanged arguments, inputs and implementation verify existing results without rewriting snapshots. Changed computation or inputs require a new linked run. `--through-batch 1`, `2`, `3` or `4` consumes complete original batches; later records remain explicitly deferred.

Processing commands return JSON with `outcome`, `mode`, verification and limitations. Exit **2** with `outcome: partial` means usable verified output with limitations; the supplied manual-policy runs remain partial even after all four batches. Exit **1** means failure; inspect `failure.json` when created. Earlier sealed states survive later failure. Exit **0** means verification passed or processing has no recorded limitations. Invalid CLI arguments also return 2, with argparse usage/error text instead of partial-result JSON. Unknown paid history cannot be replaced with zero or sealed into the integer-only schema.

## Resume, replay and recovery

The following commands operate on retained inputs; none claims a fresh source read. Use unused destination IDs for replay/recovery.

```bash
# Verify or append remaining batches with unchanged code, schema and dependencies.
.venv/bin/python skills/travel-expense-claim/scripts/run.py resume artifacts/runs/g2-20261017 --through-batch 4

# New offline run; the executed example is already retained for inspection.
.venv/bin/python skills/travel-expense-claim/scripts/run.py replay artifacts/runs/g2-20261017 \
  --run-id g2-20261017-replay --through-batch 4

# Recovery reconstruction; choose a new destination ID each time.
.venv/bin/python skills/travel-expense-claim/scripts/run.py recover artifacts/runs/g2-20261017 \
  --run-id recovery-review --through-batch 4 \
  --change-reason "Explicit retained-history reconstruction"
```

Resume refuses corrupt/missing state, inconsistent views, failed runs or changed implementation. Recovery requires complete hash-verified retained source/event history and a new destination; it does not trust damaged snapshots, replace originals, or invent original execution times. If source history is missing/corrupt, restore authoritative inputs or make a fresh acquisition. `prior-run.json`, `comparison.json`, `retention.json` and `executions/` preserve linkage, semantic divergence, hashes and actual reconstruction times. Comparison excludes run identity and source/chain bindings, which necessarily differ.

## Inspection and checks

```bash
.venv/bin/python skills/travel-expense-claim/scripts/run.py verify artifacts/runs/g2-20261017
.venv/bin/python skills/travel-expense-claim/scripts/run.py verify artifacts/runs/g2-20261017-replay
PYTHONDONTWRITEBYTECODE=1 PROJECT_D_TEST_G2_ALL_BATCHES=1 .venv/bin/python -m unittest discover -s tests -v
```

Inspect the [Operations report](artifacts/runs/g2-20261017/report.md), [CSV](artifacts/runs/g2-20261017/claims.csv), [repair queue/history](artifacts/runs/g2-20261017/repair-queue.md), [source manifest](artifacts/runs/g2-20261017/sources.json), [coverage](artifacts/runs/g2-20261017/coverage.json), [snapshots](artifacts/runs/g2-20261017/batches), and [verification evidence](artifacts/verification/g2-20261017/README.md). The [offline replay comparison](artifacts/runs/g2-20261017-replay/comparison.json) has identical semantic results for all four batches. The [recovery demonstration](artifacts/verification/g2-20261017/recovery-check.json) corrupts only a temporary copy, proves resume refuses it, and compares reconstructed states with the intact original; its temporary damaged origin is intentionally not retained.

All 127 source revisions produce 121 current claim rows. Final states: 103 reimbursed, two known-zero, one withdrawn, one rejected and 14 unresolved. There are 18 owned fact items and ten unknown entitlement totals. C19's amount-only correction does not resolve cancellation/review facts; later scoped evidence does. C121 closes after cancellation-aware reviews and a first Finance acceptance after cancellation. C18's late EUR100 stays on its original request/trip and remains unresolved. C114's supported EUR20 survives while its aggregate stays unknown and payment stays held. TC122 appears independently without a fabricated claim.

Operations starts with payable amounts, held balances, unreconciled transfers, blockers and specific next actions. A held entitlement awaiting authority is shown in the blocker table; an unknown obligation balance remains blank in CSV. Known zero is `0`. Closure requires the accepted D4 conditions; human approvals, exceptions and Finance actions remain source decisions. Local repair drafts are never sent. The verifier checks the public schema/formats, retained bytes, source/predecessor chains, money/identity references and exact output rendering; tests separately assert business expectations and adversarial boundaries. This does not certify remote authenticity or defend against an attacker rewriting every artifact.

## Gate and revision handoff

G1 and D4 were accepted. Commit [2bd09d3](https://github.com/smsnell/travel-expense-claim/commit/2bd09d3a69c1cc34a0219be0b197f164e07bfb07), **G1 Complete and Reviewed**, was pushed to origin/main. The [original preliminary run](artifacts/runs/g1-20261017-0855/report.md) and [reviewed G1 run](artifacts/runs/g1-reviewed-20261017/report.md) remain immutable and verifiable. Planning baseline: `5c9558ae360b8bde28c50e9923d4144037570136`.

G2 is accepted; the owner authorized commit/push “G2 Complete and Accepted” after focused C18/authority checks and the [revised financial summary](artifacts/runs/g2-accepted-20261017/report.md). G3 then covers final integrated verification, operational acceptance and submission handoff; stop for final owner review. Native Notion remains inaccessible, and the backup is not verified against it. Original interviews are preserved; D-4 is the latest progressive export. The owner manages supported coding-session capture verification; no self-written evidence replaces it.

Use [Project D in Work Sim](https://work-sim.catalyte.ai/s/project-d-travel-expense-claim) for stakeholder interviews. The shared [Entire setup lesson](https://classroom.google.com/c/ODcyMjA4NTkwNDk2/m/ODc0NzI2NzQzMzQ2/details) remains available to the owner.

**Interview rule.** You conduct the stakeholder interview yourself, and the questions are yours. Do not connect a coding agent or any other AI to the interview to run, script, or automate it. The interview transcript is assessed together with the code; a project whose interview was run by an agent is not scored.

- Export your interview as the original Work Sim Markdown, save one final complete file per session under `interviews/`, and commit and push it with your code. Do not rewrite the export. If the export is unavailable, contact the facilitator.

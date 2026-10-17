# Travel expense claim

Build a reusable Agent Skill for Alderbridge Consulting's travel reimbursement workflow.

## Start

1. Read the [full Project D task](https://private-pecorino-70e.notion.site/Travel-expense-claim-Task-and-submission-3da0b700541e81249039eff895f77c98) for the scope, workflow and deliverables.
2. Use **Use this template → Create a new repository** on [GitRollTraining/travel-expense-claim](https://github.com/GitRollTraining/travel-expense-claim), then clone your own repository and work there.

## G1 implementation and setup

Python 3.11+; supported Drive and Notion connectors for the invoking agent; no credentials in the Python runner. Read [AGENTS.md](AGENTS.md), [REQUIREMENTS.md](REQUIREMENTS.md), [design](DESIGN-PLAN.md), and [tracker](PROJECT-TRACKER.md). The [Skill](skills/travel-expense-claim/SKILL.md) uses four small Python modules for source validation, batch reduction, outputs/integrity, and invocation. No database or hosted service.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The host needs Python's venv/ensurepip support. This workspace lacked ensurepip, so the owner authorized official get-pip bootstrap into the project-local virtual environment. Nothing was installed system-wide. The direct dependencies are pinned; transitive dependency versions are recorded in the G1 verification evidence.

## Fresh acquisition and invocation

The agent uses supported native tools to obtain four Drive exports (three PDFs, one XLSX) and attempt the Notion policy. Follow [SOURCE-RETRIEVAL.md](SOURCE-RETRIEVAL.md) to materialize exact bytes and create `acquisition.json`. The five URLs are in `source_io.py`, sourced from the interview. Connector credentials stay with the invoking agent. `run` consumes a handoff; it does not contact MCP or authenticate the assertion of remote origin. Hashes establish retained-byte integrity.

Default: use native policy content. On failure, explicitly supply the owner-authorized Markdown copy; it remains unverified against the live page. The reviewed G1 policy/sequence fingerprints deliberately reject changed policy or interview bytes until Operations and the maintainer review rule changes. Do not edit a file merely to match the fingerprint.

The executed G1 command was:

```bash
.venv/bin/python skills/travel-expense-claim/scripts/run.py run \
  --acquisition artifacts/acquisitions/g1-2026-10-17/acquisition.json \
  --run-id g1-20261017-0855 \
  --policy-file policy/POL-2026.2.md \
  --sequencing-file interviews/interview-D-4.md \
  --through-batch 2
```

This is a historical invocation, not an instruction to relabel its old acquisition as fresh. For another fresh run, the agent must attempt all five sources again, create a new acquisition handoff and use a new run ID. Existing run IDs are refused. `--through-batch 1` processes only complete original batch 1; `2` adds complete original batch 2. Later source records are retained and inventoried as deferred, not silently dropped.

Exit 2 means a verified **partial G1 result**, not command failure. Exit 1 is failure; `failure.json` records errors when a run directory was created. No partial snapshot is published on schema failure. A failure after earlier snapshots were sealed preserves those states. Missing Finance history cannot be rendered as zero paid. Exit 0 is used by successful verification.

## Inspection and checks

```bash
.venv/bin/python skills/travel-expense-claim/scripts/run.py verify artifacts/runs/g1-20261017-0855
.venv/bin/python -m unittest discover -s tests -v
```

Inspect [report](artifacts/runs/g1-20261017-0855/report.md), [claims CSV](artifacts/runs/g1-20261017-0855/claims.csv), [repair queue](artifacts/runs/g1-20261017-0855/repair-queue.md), [manifest](artifacts/runs/g1-20261017-0855/sources.json), [coverage](artifacts/runs/g1-20261017-0855/coverage.json), and [snapshots](artifacts/runs/g1-20261017-0855/batches). `implementation.json` records code and schema digests. Tests use retained discovery bytes as labelled fixtures, plus synthetic boundary mutations; the primary output uses the fresh G1 acquisition.

G1 consumes 120 claims and all delivered review/Finance/cancellation records in batches 1–2. The report preserves unknown amounts and known zero distinctly. `allowed_cents` is the reviewed entitlement when eligibility is established; `balance_cents` is null until current authority establishes an obligation. Supported line amounts survive an unknown aggregate. Accepted Finance requests remain independent obligations when later business cancellation invalidates current eligibility. The original preliminary run retains `ready` closure candidates. The linked reviewed run applies accepted D4 and closes only current supported/reconciled claims without issues or outstanding Finance balances. No temporary D4 owners remain in new operational output.

The verifier checks public schema/formats, relative source/predecessor hashes, retained inputs, money and identity references, and exact CSV/report/queue rendering. Focused tests independently check actual amounts and authority boundaries. G1 does not establish full-assignment correctness or cryptographic protection against rewriting all artifacts; protect originals and use Git/review evidence.

## Replay, recovery and handoff boundary

```bash
.venv/bin/python skills/travel-expense-claim/scripts/run.py resume
.venv/bin/python skills/travel-expense-claim/scripts/run.py replay
.venv/bin/python skills/travel-expense-claim/scripts/run.py recover
```

These exact commands currently return exit 1, explicitly unimplemented, with no side effects. They are G2 acceptance work. Until then, preserve failed runs and their diagnostics; do not overwrite, delete or manually reseal them. Changed inputs/computation require a new linked run when G2 implements recomputation/recovery. G2 also covers batches 3–4, scoped partial responses, material corrections, Finance retry/refund/resolution and remaining cancellations. G3 covers final integrated review and handoff. G1 and D4 are accepted. Proceed through G2 after the authorized G1 commit/push, then stop for review.

Original planning baseline: `5c9558ae360b8bde28c50e9923d4144037570136`. G1 and D4 accepted; owner authorized the “G1 Complete and Reviewed” milestone commit/push. Original interviews remain unchanged; D-4 is the latest progressive export. The owner manages actual coding-session capture/checkpoint verification. Prior supported evidence and token baseline are in the tracker; this README does not certify capture for uncommitted G1 code.

Use [Project D in Work Sim](https://work-sim.catalyte.ai/s/project-d-travel-expense-claim) for stakeholder interviews. The shared [Entire setup lesson](https://classroom.google.com/c/ODcyMjA4NTkwNDk2/m/ODc0NzI2NzQzMzQ2/details) remains available to the owner.

**Interview rule.** You conduct the stakeholder interview yourself, and the questions are yours. Do not connect a coding agent or any other AI to the interview to run, script, or automate it. The interview transcript is assessed together with the code; a project whose interview was run by an agent is not scored.

- Export your interview as the original Work Sim Markdown, save one final complete file per session under `interviews/`, and commit and push it with your code. Do not rewrite the export. If the export is unavailable, contact the facilitator.

Reviewed G1 output: [Operations report](artifacts/runs/g1-reviewed-20261017/report.md), [CSV](artifacts/runs/g1-reviewed-20261017/claims.csv), [queue](artifacts/runs/g1-reviewed-20261017/repair-queue.md). Created with the same command using acquisition `artifacts/acquisitions/g1-accepted-20261017/acquisition.json`, run ID `g1-reviewed-20261017`, and `--prior-run artifacts/runs/g1-20261017-0855`. The new run records divergence and retains its predecessor unchanged. Verify either run using its exact directory; historical presentation remains verifiable.

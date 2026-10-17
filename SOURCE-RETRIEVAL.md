# Source retrieval contract

The invoking agent performs supported native reads; the Python runner consumes a verifiable acquisition handoff. The runner does not possess connector credentials or pretend to call MCP tools from Python. Neither component sends requests to employees, modifies sources, or moves money.

## Fresh run

1. The invoking agent reads the five native locations from the interview/source configuration, attempts every location during this invocation using supported Drive/Notion tools or public export routes, and records actual UTC attempt times and provider errors. A successful link is insufficient: inspect PDF page coverage, all workbook tabs/used rows, and policy section completeness. Materialize the returned bytes into an acquisition directory; do not use discovery downloads as fresh reads.
2. Write `acquisition.json` with `acquisition_id`, `mode: fresh`, `case_clock`, `source_version`, `files`. Each entry includes `source_id` (initial, updates, receipts, registers, policy-native), native `url`, local relative `path`, exact SHA-256 or null, `status` (read/unavailable), `error`, `locator`, actual `observed_at`, observed `version` or null, `acquisition_method`, and `completeness` evidence. Unavailable portions have null path/hash. Paths must stay within the acquisition directory. Entries reflect tool results, never a claim that a local file was fetched live.
3. The operator may explicitly pass `--policy-file policy/POL-2026.2.md` when native policy access fails. The runner retains and hashes it as a separate manual policy entry linked to the native URL, preserving the unavailable native entry. Record owner-supplied origin, unknown export time, and unverified live equivalence. No silent fallback. Include the unchanged interview/owner-confirmed sequencing evidence as supplemental local evidence. A policy version conflict or incomplete file is an owned failure, not permission to guess rules.
4. The runner verifies all five locations have observations, timestamps are valid, bytes match the handoff, paths are safe, and coverage is compatible. It copies exact inputs into a new run, builds `sources.json` with relative paths, then parses/validates records. It reports source availability separately from business results. Agent/tool observations remain assertions with provenance; hashes prove byte integrity, not remote authenticity.

## Reproducibility and failures

- Fresh access and deterministic recomputation are separate. Retained bytes, acquisition metadata, policy/sequence evidence, parser version and batch order make the computation reproducible even if remote documents change later.
- `resume` verifies source and predecessor bindings before consuming the next original batch. It uses the existing run's sealed source set; changed inputs require a new run.
- `replay` is explicitly offline from a retained run and makes no fresh-access claim. Keep stable source identities, obligations, event effects and money. Compare results independently; changed sealed content gets a new run linked to its predecessor.
- A missing/unreadable portion is visible with affected scope and owner. Unknown paid history that cannot truthfully fit integer `paid_cents` prevents sealing the incompatible snapshot; preserve a failure diagnostic and inputs. Never substitute zero for unknown.
- G1 implements fresh handoff validation and batch-1/2 outputs. G2 adds full resume/replay/recovery scenarios; unimplemented commands must fail explicitly, never silently behave as fresh runs.

## Bounded implementation interface

`source_io.py` will expose `prepare_sources(acquisition_path, run_dir, policy_file, sequencing_file)` returning the sealed source manifest, and `normalize(run_dir)` returning `{claims, receipts, tables}`. `claims` retains source claim/revision/batch/employee/trip/trip_revision/submitted/status/reason/related_claim_ids, line cost/receipt/first_submitted/original_amount/currency, and optional scoped exception fields. `receipts` retains receipt/cost/employee/trip/category/currency/gross/units/issued/description. `tables` retains native workbook header names and row values as decimal/date strings. Every record carries `_source_id` and `_locator`. Original bytes, not normalized summaries, remain authoritative. These are internal interfaces, not a replacement for snapshot.schema.json.

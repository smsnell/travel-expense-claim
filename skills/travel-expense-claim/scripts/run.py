#!/usr/bin/env python3
"""Local G1 invocation. Connector acquisition belongs to the invoking agent."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from engine import reduce_batch
from outputs import digest, json_text, verify, write_views
from source_io import SourceError, normalize, prepare_sources

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = Path(__file__).resolve().parent
# Rule changes require evidence review and tests, not silently reusing old logic.
POLICY_HASH = 'f547ee77729be8ad431a5ddf2e2907f94f29ad50092231191abd2f72c04f54d2'
SEQUENCE_HASH = 'c0f0a12942bd52a3c7ee215fbd42aa87eb60cadea8c5ba9887b648398e30c56e'


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json_text(value))


def execute(args):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.run_id):
        raise SourceError('run-id must be a safe nonempty directory name')
    run = ROOT / 'artifacts/runs' / args.run_id
    run.mkdir(parents=True, exist_ok=False)
    try:
        manifest = prepare_sources(args.acquisition, run, args.policy_file, args.sequencing_file)
        policy = next(e for e in manifest['files'] if e['source_id'] == 'policy-manual') if args.policy_file else next(e for e in manifest['files'] if e['source_id'] == 'policy-native')
        sequence = next(e for e in manifest['files'] if e['source_id'] == 'sequencing')
        if policy['sha256'] != POLICY_HASH or sequence['sha256'] != SEQUENCE_HASH:
            raise SourceError('Policy/sequence bytes differ from reviewed G1 rule profile; Operations must review changes before reusing this implementation')
        data = normalize(run)
        # Retain implementation identity for later reproducibility/divergence checks.
        write_new(run / 'implementation.json', {'gate': 'G1', 'observed_at': datetime.now(timezone.utc).isoformat(),
                  'files': [{'path': str(p.relative_to(ROOT)), 'sha256': digest(p)} for p in sorted(SCRIPTS.glob('*.py'))],
                  'schema_sha256': digest(ROOT / 'snapshot.schema.json'), 'rule_profile': 'POL-2026.2 + interview-D-4',
                  'preliminary_closure': False})
        if args.prior_run:
            prior = Path(args.prior_run).resolve()
            verify(prior, ROOT / 'snapshot.schema.json')
            write_new(run / 'prior-run.json', {'run_id': prior.name, 'source_manifest_sha256': digest(prior / 'sources.json'),
                      'snapshots': [{'batch_id': p.stem, 'sha256': digest(p)} for p in sorted((prior / 'batches').glob('*.json'))],
                      'reason': args.change_reason, 'mode': 'fresh linked recomputation; original retained unchanged'})
        source_hash = digest(run / 'sources.json')
        (run / 'batches').mkdir()
        states, previous = [], None
        for batch in range(1, args.through_batch + 1):
            state = reduce_batch(data, batch, manifest['case_clock'])
            state.update(schema_version='travel-claim-snapshot/2', run_id=run.name, batch_id=str(batch),
                         predecessor={'path': previous.name, 'sha256': digest(previous)} if previous else None,
                         source_binding={'path': '../sources.json', 'sha256': source_hash})
            # Validate before sealing; no partial snapshot is published.
            from jsonschema import Draft202012Validator, FormatChecker
            Draft202012Validator(json.loads((ROOT / 'snapshot.schema.json').read_text()), format_checker=FormatChecker()).validate(state)
            path = run / 'batches' / f'{batch}.json'
            write_new(path, state)
            states.append(state)
            previous = path
        write_new(run / 'coverage.json', {'parsed_claim_revisions': len(data['claims']), 'parsed_receipts': len(data['receipts']),
                  'tables': {k: len(v) for k, v in data['tables'].items()}, 'consumed': [s['coverage'] for s in states],
                  'deferred_claim_revisions': [{'claim_id': c['claim_id'], 'revision': c['revision'], 'batch_id': c['batch_id']} for c in data['claims'] if int(c['batch_id']) > args.through_batch],
                  'deferred_review_ids': [r['Decision reference'] for r in data['tables']['Review ledger'] if int(r['Arrival batch']) > args.through_batch],
                  'deferred_finance_deliveries': [r for r in data['tables']['Finance activity'] if int(r['Arrival batch']) > args.through_batch],
                  'deferred_cancellation_deliveries': [r for r in data['tables']['Travel cancellations'] if int(r['Arrival batch']) > args.through_batch]})
        write_views(run, states, manifest)
        result = verify(run, ROOT / 'snapshot.schema.json')
        write_new(run / 'verification.json', result)
        print(json_text({'outcome': 'partial', 'run': str(run), 'verification': result, 'next': 'G1/D4 accepted; remaining four-batch coverage belongs to G2'}))
        return 2
    except Exception as exc:
        write_new(run / 'failure.json', {'outcome': 'failure', 'error': str(exc), 'owner': 'Operations / Finance for source/history defects; implementation maintainer for code defects',
                  'observed_at': datetime.now(timezone.utc).isoformat(), 'next_action': 'Preserve this diagnostic and any retained inputs/sealed batches. Repair evidence or code, then create a new run; do not overwrite.'})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run')
    run.add_argument('--acquisition', required=True)
    run.add_argument('--run-id', required=True)
    run.add_argument('--policy-file')
    run.add_argument('--sequencing-file', required=True)
    run.add_argument('--through-batch', type=int, choices=(1, 2), default=2)
    run.add_argument('--prior-run')
    run.add_argument('--change-reason', default='Owner accepted D4 and requested Operations presentation improvements')
    check = commands.add_parser('verify')
    check.add_argument('run_dir')
    for name in ('resume', 'replay', 'recover'):
        commands.add_parser(name, help='G2; deliberately unimplemented')
    args = parser.parse_args()
    try:
        if args.command == 'run':
            return execute(args)
        if args.command == 'verify':
            print(json_text(verify(args.run_dir, ROOT / 'snapshot.schema.json')))
            return 0
        raise SourceError(args.command + ' is not implemented in G1; no files changed')
    except Exception as exc:
        print(json_text({'outcome': 'failure', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

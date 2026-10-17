#!/usr/bin/env python3
"""Local batch lifecycle. Native acquisition belongs to the invoking agent."""
import argparse
import copy
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile

from engine import reduce_batch
from outputs import digest, json_text, verify, write_views
from source_io import SourceError, URLS, normalize, prepare_sources, _utc

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = Path(__file__).resolve().parent
POLICY_HASH = 'f547ee77729be8ad431a5ddf2e2907f94f29ad50092231191abd2f72c04f54d2'
SEQUENCE_HASH = 'c0f0a12942bd52a3c7ee215fbd42aa87eb60cadea8c5ba9887b648398e30c56e'


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json_text(value))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def implementation():
    return {'gate': 'G2', 'files': [{'path': str(p.relative_to(ROOT)), 'sha256': digest(p)} for p in sorted(SCRIPTS.glob('*.py'))],
            'schema_sha256': digest(ROOT / 'snapshot.schema.json'), 'requirements_sha256': digest(ROOT / 'requirements.txt'),
            'python': platform.python_version(), 'dependencies': {p: version(p) for p in ('pypdf', 'openpyxl', 'jsonschema', 'attrs', 'jsonschema-specifications', 'referencing', 'rpds-py', 'et-xmlfile')},
            'rule_profile': 'POL-2026.2 + interview-D-4', 'preliminary_closure': False}


def code_identity(value):
    if not isinstance(value, dict):
        raise ValueError('Invalid retained implementation identity')
    return {k: v for k, v in value.items() if k != 'observed_at'}


def inside(run, relative):
    path = (run / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(run.resolve()) or not path.is_file():
        raise SourceError('Unsafe or missing retained input: ' + str(relative))
    return path


def retained(run, recovery=False):
    """Validate the complete original hash manifest independently of snapshots."""
    manifest = load(run / 'sources.json')
    if manifest['run_id'] != run.name:
        raise SourceError('Retained source manifest run identity differs')
    entries = manifest['files']
    by_id = {e['source_id']: e for e in entries}
    if len(by_id) != len(entries) or not set(URLS) <= set(by_id) or 'sequencing' not in by_id:
        raise SourceError('Incomplete retained source manifest: all five native observations and sequencing required')
    for sid, url in URLS.items():
        if by_id[sid]['url'] != url:
            raise SourceError('Unexpected native source URL: ' + sid)
    retained_paths = set()
    for e in entries:
        _utc(e['observed_at'])
        if e['status'] == 'read':
            relative = Path(e['path'])
            if len(relative.parts) != 2 or relative.parts[0] != 'inputs' or e['path'] in retained_paths:
                raise SourceError('Unsafe or duplicate retained input path: ' + str(e['path']))
            retained_paths.add(e['path'])
            if digest(inside(run, e['path'])) != e['sha256']:
                raise SourceError('Retained input digest mismatch: ' + e['source_id'])
        elif e['status'] != 'unavailable' or e['source_id'] != 'policy-native' or e['path'] is not None or e['sha256'] is not None or not e['error']:
            raise SourceError('Missing/incompatible required retained source: ' + e['source_id'])
    policy = by_id.get('policy-manual', by_id['policy-native'])
    if policy['status'] != 'read' or policy['sha256'] != POLICY_HASH or by_id['sequencing']['sha256'] != SEQUENCE_HASH:
        raise SourceError('Policy/sequence differ from reviewed rule profile; Operations review required')
    if (run / 'retention.json').exists():
        seal = load(run / 'retention.json')
        if seal['source_manifest_sha256'] != digest(run / 'sources.json'):
            raise SourceError('Retained source manifest digest mismatch')
        if not recovery and seal['implementation_sha256'] != digest(run / 'implementation.json'):
            raise SourceError('Retained implementation digest mismatch')
    # Parsers check complete PDF page/card sequences and all workbook tabs/rows.
    data = normalize(run)
    if not data['tables'].get('Finance activity'):
        raise SourceError('Unknown paid history; Finance must restore complete retained history')
    return manifest, data


def paths(run):
    return sorted((run / 'batches').glob('*.json'), key=lambda p: int(p.stem))


def semantic(state):
    if not isinstance(state, dict):
        raise ValueError('Invalid retained snapshot object')
    return {k: v for k, v in state.items() if k not in ('run_id', 'predecessor', 'source_binding', 'execution', 'executed_at', 'reconstructed_at')}


def request(args):
    result = {k: v for k, v in vars(args).items() if k not in ('run_id',)}
    for key in ('acquisition', 'policy_file', 'sequencing_file'):
        if result.get(key):
            path = Path(result[key]).resolve()
            result[key] = {'path': str(path), 'sha256': digest(path)}
            if key == 'acquisition':
                result[key]['retained_byte_identity'] = [
                    {'source_id': e['source_id'], 'sha256': digest(inside(path.parent, e['path']))}
                    for e in load(path)['files'] if e['status'] == 'read']
    for key in ('prior_run', 'run_dir'):
        if result.get(key):
            result[key] = str(Path(result[key]).resolve())
    return result


def retry(run, invocation):
    if not (run / 'request.json').is_file() or load(run / 'request.json') != invocation:
        raise SourceError('File exists: run-id belongs to a different invocation; use a new run-id')
    if code_identity(load(run / 'implementation.json')) != implementation():
        raise SourceError('Implementation changed; use replay with a new run-id')
    retained(run)
    if (run / 'failure.json').exists():
        raise SourceError('Failed prior run; recover into a new linked run; no sealed state overwritten')
    result = verify(run, ROOT / 'snapshot.schema.json')
    return outcome(run, result, retry=True)


def outcome(run, verification, **extra):
    manifest = load(run / 'sources.json')
    state = load(paths(run)[-1])
    limits = list(state['coverage'].get('limits', []))
    if any(e['status'] == 'unavailable' for e in manifest['files']):
        limits.append('Native Notion policy unavailable; manual policy export time unknown and live equivalence unverified')
    partial = bool(limits or state['coverage'].get('deferred_batches') or state['coverage']['status'].startswith('partial'))
    print(json_text({'outcome': 'partial' if partial else 'success', 'run': str(run), 'mode': manifest['mode'],
                     'verification': verification, 'limitations': limits, **extra}))
    return 2 if partial else 0


def coverage(data, states):
    through = int(states[-1]['batch_id'])
    return {'parsed_claim_revisions': len(data['claims']), 'parsed_receipts': len(data['receipts']),
            'tables': {k: len(v) for k, v in data['tables'].items()}, 'consumed': [s['coverage'] for s in states],
            'deferred_claim_revisions': [{'claim_id': c['claim_id'], 'revision': c['revision'], 'batch_id': c['batch_id']} for c in data['claims'] if int(c['batch_id']) > through],
            'deferred_review_ids': [r['Decision reference'] for r in data['tables']['Review ledger'] if int(r['Arrival batch']) > through],
            'deferred_finance_deliveries': [r for r in data['tables']['Finance activity'] if int(r['Arrival batch']) > through],
            'deferred_cancellation_deliveries': [r for r in data['tables']['Travel cancellations'] if int(r['Arrival batch']) > through]}


def publish(run, states, manifest, data):
    # Only current derived views are replaceable. Sealed batches never are.
    with tempfile.TemporaryDirectory(prefix='.views-', dir=run) as directory:
        stage = Path(directory)
        write_views(stage, states, manifest)
        write_new(stage / 'coverage.json', coverage(data, states))
        for path in stage.iterdir():
            path.replace(run / path.name)
    result = verify(run, ROOT / 'snapshot.schema.json')
    temporary = run / '.verification.json'
    temporary.write_text(json_text(result), encoding='utf-8')
    temporary.replace(run / 'verification.json')
    return result


def consume(run, manifest, data, through, states=()):
    from jsonschema import Draft202012Validator, FormatChecker
    validator = Draft202012Validator(load(ROOT / 'snapshot.schema.json'), format_checker=FormatChecker())
    states = list(states)
    (run / 'batches').mkdir(exist_ok=True)
    (run / 'executions').mkdir(exist_ok=True)
    previous = run / 'batches' / f'{len(states)}.json' if states else None
    source_hash = digest(run / 'sources.json')
    for batch in range(len(states) + 1, through + 1):
        state = reduce_batch(data, batch, manifest['case_clock'])
        state.update(schema_version='travel-claim-snapshot/2', run_id=run.name, batch_id=str(batch),
                     predecessor={'path': previous.name, 'sha256': digest(previous)} if previous else None,
                     source_binding={'path': '../sources.json', 'sha256': source_hash})
        validator.validate(state)
        path = run / 'batches' / f'{batch}.json'
        write_new(path, state)
        write_new(run / 'executions' / f'{batch}.json', {'batch_id': str(batch), 'sealed_at': now(),
                  'mode': manifest['mode'], 'snapshot_sha256': digest(path),
                  'note': 'Actual reconstruction time; source business/event/observation times preserved' if manifest['mode'].startswith('offline') else 'Actual local execution time'})
        states.append(state)
        previous = path
    return states


def failure(run, exc):
    if not (run / 'failure.json').exists():
        write_new(run / 'failure.json', {'outcome': 'failure', 'error': str(exc), 'observed_at': now(),
                  'owner': 'Operations / Finance for source/history defects; implementation maintainer for code defects',
                  'next_action': 'Preserve inputs and seals. Restore complete source history or implementation, then recover into a NEW linked run; no prior seals overwritten.'})


def link(prior, mode, reason):
    return {'run_id': prior.name, 'path': str(prior), 'source_manifest_sha256': digest(prior / 'sources.json'),
            'snapshots': [{'batch_id': p.stem, 'sha256': digest(p)} for p in paths(prior)],
            'reason': reason, 'mode': mode, 'linked_at': now()}


def execute(args):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.run_id):
        raise SourceError('run-id must be a safe nonempty directory name')
    run = ROOT / 'artifacts/runs' / args.run_id
    if run.exists() and not (run / 'request.json').is_file():
        raise SourceError('File exists: run-id has no matching invocation identity; use a new run-id')
    invocation = request(args)
    through = args.through_batch
    if run.exists():
        return retry(run, invocation)
    run.mkdir(parents=True)
    try:
        write_new(run / 'request.json', invocation)
        if args.command == 'run':
            # prepare_sources needs an empty directory; request is retained after acquisition.
            (run / 'request.json').unlink()
            manifest = prepare_sources(args.acquisition, run, args.policy_file, args.sequencing_file)
            write_new(run / 'request.json', invocation)
            if args.prior_run:
                prior = Path(args.prior_run).resolve()
                verify(prior, ROOT / 'snapshot.schema.json')
                write_new(run / 'prior-run.json', link(prior, 'fresh linked recomputation', args.change_reason))
        else:
            prior = Path(args.run_dir).resolve()
            manifest, _ = retained(prior, recovery=args.command == 'recover')
            if args.command == 'replay':
                if (prior / 'failure.json').exists():
                    raise SourceError('Replay requires a verified prior run; use recover for failed/missing/corrupt state')
                verify(prior, ROOT / 'snapshot.schema.json')
            manifest = copy.deepcopy(manifest)
            for e in manifest['files']:
                if e['status'] == 'read':
                    source = inside(prior, e['path'])
                    destination = run / e['path']
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
            manifest.update(run_id=run.name, mode='offline-recovery' if args.command == 'recover' else 'offline-replay',
                            origin_run_id=prior.name, retained_from=str(prior), reconstructed_at=now(),
                            provenance_note=manifest.get('provenance_note', '') + ' Offline retained-input recomputation; no fresh native access attempted or claimed.')
            write_new(run / 'sources.json', manifest)
            write_new(run / 'prior-run.json', link(prior, manifest['mode'], args.change_reason))
            if through is None:
                through = max((int(p.stem) for p in paths(prior)), default=0)
                if not through:
                    raise SourceError('Missing original states: recovery requires explicit --through-batch 1..4')
        write_new(run / 'implementation.json', dict(implementation(), observed_at=now()))
        write_new(run / 'retention.json', {'source_manifest_sha256': digest(run / 'sources.json'),
                  'implementation_sha256': digest(run / 'implementation.json'), 'sealed_at': now()})
        manifest, data = retained(run)
        states = consume(run, manifest, data, through)
        if args.command in ('replay', 'recover'):
            comparisons = []
            for p in paths(prior):
                if int(p.stem) > len(states):
                    continue
                try:
                    old = load(p)
                    changed = sorted(k for k in set(semantic(old)) | set(semantic(states[int(p.stem)-1])) if semantic(old).get(k) != semantic(states[int(p.stem)-1]).get(k))
                    comparisons.append({'batch_id': p.stem, 'equivalent': not changed, 'changed_fields': changed})
                except (ValueError, KeyError, TypeError) as exc:
                    comparisons.append({'batch_id': p.stem, 'equivalent': False, 'comparison_unavailable': str(exc)})
            try:
                prior_implementation = code_identity(load(prior / 'implementation.json'))
            except (OSError, ValueError, TypeError):
                prior_implementation = None
            write_new(run / 'comparison.json', {'origin_run_id': prior.name, 'mode': manifest['mode'],
                      'implementation_changed': prior_implementation != implementation() if prior_implementation else None,
                      'batches': comparisons, 'note': 'Semantic comparison excludes run identity and chain/source bindings. Original run retained unchanged; actual reconstruction times recorded in executions/.'})
        result = publish(run, states, manifest, data)
        return outcome(run, result)
    except Exception as exc:
        failure(run, exc)
        raise


def resume(args):
    run = Path(args.run_dir).resolve()
    if (run / 'failure.json').exists():
        raise SourceError('Failed prior run; recover into a NEW linked run')
    # Verification includes original predecessor/source hashes and current views.
    try:
        verify(run, ROOT / 'snapshot.schema.json')
        manifest, data = retained(run)
    except Exception as exc:
        raise SourceError(f'Cannot resume missing/corrupt state or inconsistent outputs: {exc}. Use recover with a NEW run-id.') from exc
    if code_identity(load(run / 'implementation.json')) != implementation():
        raise SourceError('Implementation/schema/dependencies changed; replay into a NEW linked run')
    states = [load(p) for p in paths(run)]
    if args.through_batch < len(states):
        raise SourceError('Cannot resume backwards; original sealed batches retained')
    if args.through_batch == len(states):
        return outcome(run, verify(run, ROOT / 'snapshot.schema.json'), retry=True)
    try:
        states = consume(run, manifest, data, args.through_batch, states)
        return outcome(run, publish(run, states, manifest, data))
    except Exception as exc:
        failure(run, exc)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    fresh = commands.add_parser('run')
    fresh.add_argument('--acquisition', required=True)
    fresh.add_argument('--run-id', required=True)
    fresh.add_argument('--policy-file')
    fresh.add_argument('--sequencing-file', required=True)
    fresh.add_argument('--through-batch', type=int, choices=(1, 2, 3, 4), default=4)
    fresh.add_argument('--prior-run')
    fresh.add_argument('--change-reason', default='Fresh linked source acquisition')
    check = commands.add_parser('verify')
    check.add_argument('run_dir')
    continued = commands.add_parser('resume')
    continued.add_argument('run_dir')
    continued.add_argument('--through-batch', type=int, choices=(1, 2, 3, 4), default=4)
    for name in ('replay', 'recover'):
        command = commands.add_parser(name)
        command.add_argument('run_dir')
        command.add_argument('--run-id', required=True)
        command.add_argument('--through-batch', type=int, choices=(1, 2, 3, 4))
        command.add_argument('--change-reason', default='Explicit offline retained-input recomputation')
    args = parser.parse_args()
    try:
        if args.command == 'verify':
            print(json_text(verify(args.run_dir, ROOT / 'snapshot.schema.json')))
            return 0
        if args.command == 'resume':
            return resume(args)
        return execute(args)
    except Exception as exc:
        print(json_text({'outcome': 'failure', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

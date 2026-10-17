"""Offline lifecycle checks using complete retained actual source/event bytes."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOT = Path(os.environ.get('PROJECT_D_IMPLEMENTATION_ROOT', ROOT))
SCRIPTS = IMPLEMENTATION_ROOT / 'skills/travel-expense-claim/scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('lifecycle_under_test', SCRIPTS / 'run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
ORIGINAL = IMPLEMENTATION_ROOT / 'artifacts/runs/g1-reviewed-20261017'


def fingerprints(root):
    return {str(p.relative_to(root)): runner.digest(p) for p in root.rglob('*') if p.is_file()}


def replay_args(prior, name, through=2, command='replay'):
    return argparse.Namespace(command=command, run_dir=str(prior), run_id=name,
                              through_batch=through, change_reason='Explicit lifecycle test; no fresh access')


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = runner.implementation()
        cls.retained_original = fingerprints(ORIGINAL)
        cls.fixture = tempfile.TemporaryDirectory()
        fixture_root = Path(cls.fixture.name)
        shutil.copy(IMPLEMENTATION_ROOT / 'snapshot.schema.json', fixture_root)
        with patch.object(runner, 'ROOT', fixture_root), patch.object(runner, 'implementation', return_value=cls.identity), contextlib.redirect_stdout(io.StringIO()):
            runner.execute(replay_args(ORIGINAL, 'base'))
        cls.baseline = fixture_root / 'artifacts/runs/base'

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()
        assert fingerprints(ORIGINAL) == cls.retained_original, 'Original G1 run changed during lifecycle tests'

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copy(IMPLEMENTATION_ROOT / 'snapshot.schema.json', self.root)
        self.base = Path(shutil.copytree(self.baseline, self.root / 'artifacts/runs/base'))
        self.root_patch = patch.object(runner, 'ROOT', self.root)
        self.identity_patch = patch.object(runner, 'implementation', return_value=self.identity)
        self.root_patch.start()
        self.identity_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.identity_patch.stop)

    def execute(self, args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = runner.execute(args)
        return code, json.loads(output.getvalue())

    def test_replay_preserves_all_semantic_states_and_financial_effects(self):
        before = fingerprints(self.base)
        code, result = self.execute(replay_args(self.base, 'unchanged'))
        replay = self.root / 'artifacts/runs/unchanged'
        comparison = runner.load(replay / 'comparison.json')
        self.assertEqual(code, 2)  # Native Notion access is still unavailable.
        self.assertEqual(result['mode'], 'offline-replay')
        self.assertTrue(all(row['equivalent'] for row in comparison['batches']))
        for a, b in zip(runner.paths(self.base), runner.paths(replay)):
            self.assertEqual(runner.semantic(runner.load(a)), runner.semantic(runner.load(b)))
        original_manifest = runner.load(self.base / 'sources.json')
        copied_manifest = runner.load(replay / 'sources.json')
        self.assertEqual(original_manifest['files'], copied_manifest['files'])
        self.assertIn('unverified', next(e for e in copied_manifest['files'] if e['source_id'] == 'policy-manual')['live_equivalence'])
        self.assertEqual(before, fingerprints(self.base))

    def test_idempotent_retry_and_argument_identity(self):
        args = replay_args(self.base, 'retry')
        self.execute(args)
        destination = self.root / 'artifacts/runs/retry'
        before = fingerprints(destination)
        _, result = self.execute(copy.deepcopy(args))
        self.assertTrue(result['retry'])
        self.assertEqual(before, fingerprints(destination))
        args.change_reason = 'Changed request identity'
        with self.assertRaisesRegex(runner.SourceError, 'different invocation'):
            self.execute(args)
        self.assertEqual(before, fingerprints(destination))

    def test_fresh_handoff_path_and_retry_bind_actual_acquisition_bytes(self):
        # Local fixture assertions exercise the handoff contract only; no native
        # source reads are asserted by this test or used for delivery evidence.
        acquisition = self.root / 'synthetic-acquisition'
        acquisition.mkdir()
        source_manifest = runner.load(self.base / 'sources.json')
        entries = [copy.deepcopy(e) for e in source_manifest['files'] if e['source_id'] in runner.URLS]
        for e in entries:
            e['acquisition_method'] = 'synthetic_lifecycle_fixture_only'
            if e['status'] == 'read':
                destination = acquisition / Path(e['path']).name
                shutil.copyfile(self.base / e['path'], destination)
                e['path'] = destination.name
        handoff = {k: source_manifest[k] for k in ('source_version', 'case_clock')}
        handoff.update(mode='fresh', acquisition_id='synthetic-lifecycle-fixture', files=entries)
        handoff_path = acquisition / 'acquisition.json'
        handoff_path.write_text(json.dumps(handoff))
        args = argparse.Namespace(command='run', acquisition=str(handoff_path), run_id='fresh-fixture',
                                  policy_file=str(self.base / 'inputs/policy-manual.md'),
                                  sequencing_file=str(self.base / 'inputs/sequencing.md'),
                                  through_batch=2, prior_run=None, change_reason='Synthetic test')
        self.execute(args)
        run = self.root / 'artifacts/runs/fresh-fixture'
        before = fingerprints(run)
        self.execute(args)
        self.assertEqual(before, fingerprints(run))
        path = acquisition / entries[0]['path']
        path.write_bytes(path.read_bytes() + b'changed acquisition bytes')
        with self.assertRaisesRegex(runner.SourceError, 'different invocation'):
            self.execute(args)
        self.assertEqual(before, fingerprints(run))

    def test_resume_uses_original_sources_and_preserves_first_seal(self):
        self.execute(replay_args(self.base, 'one', through=1))
        run = self.root / 'artifacts/runs/one'
        first = (run / 'batches/1.json').read_bytes()
        sources = (run / 'sources.json').read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            runner.resume(argparse.Namespace(run_dir=str(run), through_batch=2))
            runner.resume(argparse.Namespace(run_dir=str(run), through_batch=2))
        self.assertEqual(first, (run / 'batches/1.json').read_bytes())
        self.assertEqual(sources, (run / 'sources.json').read_bytes())
        self.assertEqual(runner.load(run / 'batches/2.json')['predecessor']['sha256'], runner.digest(run / 'batches/1.json'))
        runner.verify(run, self.root / 'snapshot.schema.json')

    def test_resume_rejects_changed_implementation(self):
        changed = dict(self.identity, python='changed-test-runtime')
        before = fingerprints(self.base)
        with patch.object(runner, 'implementation', return_value=changed):
            with self.assertRaisesRegex(runner.SourceError, 'changed.*NEW linked run'):
                runner.resume(argparse.Namespace(run_dir=str(self.base), through_batch=2))
        self.assertEqual(before, fingerprints(self.base))

    def test_changed_recomputation_creates_linked_run_and_reports_divergence(self):
        before = fingerprints(self.base)
        actual = runner.reduce_batch
        def changed(data, batch, clock):
            state = actual(data, batch, clock)
            state['claims'][0]['reason'] += ' Synthetic implementation divergence.'
            return state
        with patch.object(runner, 'reduce_batch', side_effect=changed):
            self.execute(replay_args(self.base, 'changed'))
        run = self.root / 'artifacts/runs/changed'
        comparison = runner.load(run / 'comparison.json')
        self.assertTrue(all('claims' in row['changed_fields'] for row in comparison['batches']))
        self.assertEqual(runner.load(run / 'prior-run.json')['run_id'], 'base')
        self.assertEqual(before, fingerprints(self.base))

    def test_missing_predecessor_cannot_resume_but_recovers_from_complete_bytes(self):
        (self.base / 'batches/1.json').unlink()
        before = fingerprints(self.base)
        with self.assertRaisesRegex(runner.SourceError, 'Cannot resume.*NEW run-id'):
            runner.resume(argparse.Namespace(run_dir=str(self.base), through_batch=2))
        lower_bound = runner.now()
        _, result = self.execute(replay_args(self.base, 'recovered', command='recover'))
        run = self.root / 'artifacts/runs/recovered'
        self.assertEqual(result['mode'], 'offline-recovery')
        self.assertEqual(len(runner.paths(run)), 2)
        self.assertGreaterEqual(runner.load(run / 'executions/1.json')['sealed_at'], lower_bound)
        self.assertEqual(runner.load(run / 'sources.json')['files'], runner.load(self.base / 'sources.json')['files'])
        self.assertEqual(before, fingerprints(self.base))

    def test_corrupt_snapshot_recovery_does_not_trust_snapshot_content(self):
        (self.base / 'batches/1.json').write_text('{broken JSON')
        self.execute(replay_args(self.base, 'recovered', command='recover'))
        recovered = self.root / 'artifacts/runs/recovered'
        original_second = runner.load(self.baseline / 'batches/2.json')
        self.assertEqual(runner.semantic(original_second), runner.semantic(runner.load(recovered / 'batches/2.json')))
        self.assertFalse(runner.load(recovered / 'comparison.json')['batches'][0]['equivalent'])

    def test_missing_old_implementation_does_not_prevent_source_history_recovery(self):
        (self.base / 'implementation.json').unlink()
        self.execute(replay_args(self.base, 'recovered', command='recover'))
        run = self.root / 'artifacts/runs/recovered'
        self.assertIsNone(runner.load(run / 'comparison.json')['implementation_changed'])
        self.assertEqual(runner.semantic(runner.load(self.baseline / 'batches/2.json')),
                         runner.semantic(runner.load(run / 'batches/2.json')))

    def test_corrupt_retained_input_or_manifest_prevents_recovery(self):
        for target in ('inputs/initial.pdf', 'sources.json'):
            with self.subTest(target=target):
                path = self.base / target
                old = path.read_bytes()
                if target == 'sources.json':
                    value = runner.load(path)
                    value['source_version'] = 'CORRUPT'
                    path.write_text(json.dumps(value))
                else:
                    path.write_bytes(old + b'corrupt retained bytes')
                before = fingerprints(self.base)
                with self.assertRaisesRegex(runner.SourceError, 'digest mismatch'):
                    self.execute(replay_args(self.base, target.replace('/', '-').replace('.', '-'), command='recover'))
                self.assertEqual(before, fingerprints(self.base))
                path.write_bytes(old)

    def test_interrupted_view_publication_requires_new_linked_recovery(self):
        self.execute(replay_args(self.base, 'one', through=1))
        run = self.root / 'artifacts/runs/one'
        with patch.object(runner, 'publish', side_effect=OSError('Synthetic interrupted view publication')):
            with self.assertRaisesRegex(OSError, 'interrupted'):
                runner.resume(argparse.Namespace(run_dir=str(run), through_batch=2))
        self.assertTrue((run / 'batches/2.json').is_file())
        before = fingerprints(run)
        with self.assertRaisesRegex(runner.SourceError, 'Failed prior run'):
            runner.resume(argparse.Namespace(run_dir=str(run), through_batch=2))
        self.execute(replay_args(run, 'recovered', command='recover'))
        runner.verify(self.root / 'artifacts/runs/recovered', self.root / 'snapshot.schema.json')
        self.assertEqual(before, fingerprints(run))

    @unittest.skipUnless(os.environ.get('PROJECT_D_TEST_G2_ALL_BATCHES') == '1',
                         'Enable after the all-four-batch reducer/verifier integration is ready')
    def test_all_four_batches_resume_replay_and_corrupt_state_recovery(self):
        self.execute(replay_args(self.base, 'all', through=1))
        run = self.root / 'artifacts/runs/all'
        first = (run / 'batches/1.json').read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            runner.resume(argparse.Namespace(run_dir=str(run), through_batch=4))
        self.assertEqual(first, (run / 'batches/1.json').read_bytes())
        final = runner.load(run / 'batches/4.json')
        self.assertEqual(len(runner.paths(run)), 4)
        self.assertEqual(next(c['revision'] for c in final['claims'] if c['claim_id'] == 'C19'), 3)
        self.assertEqual(final['coverage']['deferred_batches'], [])
        self.assertEqual(len({r['request_id'] for r in final['requests']}), len(final['requests']))
        self.assertEqual(len(set(final['admitted_event_ids'])), len(final['admitted_event_ids']))
        before = fingerprints(run)
        self.execute(replay_args(run, 'all-replay', through=4))
        replay = self.root / 'artifacts/runs/all-replay'
        self.assertTrue(all(row['equivalent'] for row in runner.load(replay / 'comparison.json')['batches']))
        self.assertEqual(runner.semantic(final), runner.semantic(runner.load(replay / 'batches/4.json')))
        self.assertEqual(before, fingerprints(run))
        (run / 'batches/3.json').write_text('{synthetic damaged third batch')
        damaged = fingerprints(run)
        self.execute(replay_args(run, 'all-recovered', through=4, command='recover'))
        recovered = self.root / 'artifacts/runs/all-recovered'
        runner.verify(recovered, self.root / 'snapshot.schema.json')
        self.assertEqual(runner.semantic(final), runner.semantic(runner.load(recovered / 'batches/4.json')))
        self.assertEqual(damaged, fingerprints(run))


if __name__ == '__main__':
    unittest.main()

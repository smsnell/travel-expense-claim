"""Verify retained G1 artifacts and fail-closed CLI behavior without fresh access."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOT = Path(os.environ.get('PROJECT_D_IMPLEMENTATION_ROOT', ROOT))
SCRIPTS = IMPLEMENTATION_ROOT / 'skills/travel-expense-claim/scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('g1_outputs_under_test', SCRIPTS / 'outputs.py')
outputs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outputs)
RUN = IMPLEMENTATION_ROOT / 'artifacts/runs/g1-20261017-0855'
SCHEMA = IMPLEMENTATION_ROOT / 'snapshot.schema.json'


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


class OutputIntegrityTests(unittest.TestCase):
    def test_financial_summary_keeps_held_entitlements_and_original_money_distinct(self):
        state = json.loads((IMPLEMENTATION_ROOT / 'artifacts/runs/g2-20261017/batches/4.json').read_text())
        summary = outputs.financial_summary(state)
        self.assertEqual(summary, {
            'payable_cents': 0, 'known_held_entitlement_cents': 128001,
            'unknown_held_claims': 10, 'supported_inside_unknown_cents': 6000,
            'unreconciled_paid_cents': 10000, 'unsettled_commitments_cents': 0,
        })
        # C18's original transfer is already represented separately; changing
        # that aggregate must not silently offset its replacement entitlement.
        c18 = next(c for c in state['claims'] if c['claim_id']=='C18')
        c18['paid_cents'] = 20000
        self.assertEqual(outputs.financial_summary(state)['known_held_entitlement_cents'], 128001)

    def copy_run(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        # Manifest/snapshot run identities must remain valid while testing damage.
        return Path(shutil.copytree(RUN, Path(temporary.name) / RUN.name))

    def test_actual_retained_g1_run_verifies(self):
        before = fingerprint(RUN)
        result = outputs.verify(RUN, SCHEMA)
        self.assertEqual((result['status'], result['run_id'], result['snapshots'], result['current_claims']),
                         ('verified', RUN.name, 2, 120))
        self.assertEqual(fingerprint(RUN), before)

    def test_retained_input_corruption_fails_byte_binding(self):
        run = self.copy_run()
        manifest = json.loads((run / 'sources.json').read_text())
        entry = next(e for e in manifest['files'] if e['status'] == 'read')
        path = run / entry['path']
        path.write_bytes(path.read_bytes() + b'corrupted fixture copy')
        with self.assertRaisesRegex(outputs.SourceError, 'digest mismatch'):
            outputs.verify(run, SCHEMA)

    def test_predecessor_digest_corruption_fails_chain(self):
        run = self.copy_run()
        path = run / 'batches/2.json'
        state = json.loads(path.read_text())
        state['predecessor']['sha256'] = '0' * 64
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(outputs.SourceError, 'digest mismatch'):
            outputs.verify(run, SCHEMA)

    def test_missing_first_batch_fails_sequence(self):
        run = self.copy_run()
        (run / 'batches/1.json').unlink()
        with self.assertRaisesRegex(outputs.SourceError, 'missing/unsupported sealed batch sequence'):
            outputs.verify(run, SCHEMA)

    def test_csv_mismatch_fails_view_consistency(self):
        run = self.copy_run()
        path = run / 'claims.csv'
        path.write_text(path.read_text().replace('10000', '99999', 1))
        with self.assertRaisesRegex(outputs.SourceError, 'view differs from sealed state: claims.csv'):
            outputs.verify(run, SCHEMA)

    def test_last_snapshot_semantic_money_damage_fails_without_successor_hash(self):
        run = self.copy_run()
        path = run / 'batches/2.json'
        state = json.loads(path.read_text())
        claim = next(c for c in state['claims'] if c['claim_id'] == 'C01')
        claim['paid_cents'] += 1
        # Batch 2 has no successor digest; predecessor and all retained inputs
        # remain valid. This must fail semantic validation before view checks.
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(outputs.SourceError, 'paid differs from admitted G1 transfers'):
            outputs.verify(run, SCHEMA)

    def test_cli_missing_required_arguments_and_existing_run_leave_files_unchanged(self):
        before = fingerprint(RUN)
        for command in ('resume', 'replay', 'recover'):
            with self.subTest(command=command):
                result = subprocess.run([sys.executable, str(SCRIPTS / 'run.py'), command], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn('required', result.stderr)
                self.assertEqual(fingerprint(RUN), before)
        result = subprocess.run([sys.executable, str(SCRIPTS / 'run.py'), 'run', '--run-id', RUN.name,
                                 '--acquisition', '/nonexistent/acquisition.json', '--sequencing-file', '/nonexistent/sequence.md'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        error = json.loads(result.stderr)
        self.assertEqual(error['outcome'], 'failure')
        self.assertIn('File exists', error['error'])
        self.assertEqual(fingerprint(RUN), before)


if __name__ == '__main__':
    unittest.main()

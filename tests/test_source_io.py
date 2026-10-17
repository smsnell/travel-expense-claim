"""Discovery bytes exercise parsing only; these tests make no fresh-access claim."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('source_io', ROOT / 'skills/travel-expense-claim/scripts/source_io.py')
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


class SourceIOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.run = self.base / 'run-test'
        self.run.mkdir()
        self.acq = self.base / 'acquisition'
        self.acq.mkdir()
        paths = {'initial': '2026-10-17/claims-initial.pdf', 'updates': '2026-10-17/claims-updates.pdf',
                 'receipts': '2026-10-16/receipts.pdf', 'registers': '2026-10-16/travel-registers.xlsx'}
        entries = []
        for sid, url in s.URLS.items():
            entry = dict(source_id=sid, url=url, path=None, sha256=None, status='unavailable', error='Synthetic acquisition assertion for test; native policy inaccessible', locator='complete source', observed_at='2026-10-17T04:00:00Z', version=None, acquisition_method='test_fixture_only', completeness={'fixture': True})
            if sid in paths:
                path = self.acq / Path(paths[sid]).name
                shutil.copyfile(ROOT / 'artifacts/discovery' / paths[sid], path)
                entry.update(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='read', error=None, version='SRC-D-3')
            entries.append(entry)
        self.handoff = dict(acquisition_id='synthetic-parser-test', mode='fresh', case_clock='2026-11-15', source_version='SRC-D-3', files=entries)
        self.handoff_path = self.acq / 'acquisition.json'

    def prepare(self):
        self.handoff_path.write_text(json.dumps(self.handoff))
        return s.prepare_sources(self.handoff_path, self.run, ROOT / 'policy/POL-2026.2.md', ROOT / 'interviews/interview-D-3.md')

    def test_retains_and_parses_complete_discovery_bytes(self):
        manifest = self.prepare()
        parsed = s.normalize(self.run)
        self.assertEqual((len(parsed['claims']), len(parsed['receipts'])), (127, 203))
        self.assertEqual(tuple(parsed['tables']), s.TABS)
        self.assertEqual(sum(c['batch_id'] == '1' for c in parsed['claims']), 120)
        self.assertEqual(sum(c['batch_id'] == '2' for c in parsed['claims']), 0)
        self.assertEqual(sum(c['batch_id'] == '3' for c in parsed['claims']), 6)
        self.assertEqual(sum(c['batch_id'] == '4' for c in parsed['claims']), 1)
        final = next(c for c in parsed['claims'] if c['claim_id'] == 'C19' and c['revision'] == 3)
        self.assertIn('refund reconciles prior reimbursement', final['exception']['reason'])
        self.assertEqual(final['exception']['allowed_original_amount'], '80.00')
        self.assertEqual(final['exception']['covered_issues'], ['Travel cancellation'])
        self.assertEqual(parsed['tables']['Trips'][0]['Start date'], '2026-09-02')
        self.assertEqual(parsed['tables']['Trips'][0]['International'], 'False')
        self.assertEqual(parsed['tables']['Review ledger'][0]['Decision time (UTC)'], '2026-09-03T12:00:00Z')
        for entry in manifest['files']:
            if entry['status'] == 'read':
                self.assertEqual(s._hash(self.run / entry['path']), entry['sha256'])
        native = next(e for e in manifest['files'] if e['source_id'] == 'policy-native')
        self.assertEqual(native['status'], 'unavailable')
        manual = next(e for e in manifest['files'] if e['source_id'] == 'policy-manual')
        self.assertEqual(manual['live_equivalence'], 'unverified')
        path = self.run / manifest['files'][0]['path']
        path.write_bytes(path.read_bytes() + b'tampered')
        with self.assertRaisesRegex(s.SourceError, 'SHA-256'):
            s.normalize(self.run)

    def test_rejects_bad_handoff_before_retaining_bytes(self):
        original = copy.deepcopy(self.handoff)
        mutations = [
            ('escape', lambda e: e.update(path='../outside.pdf'), 'escapes|missing'),
            ('digest', lambda e: e.update(sha256='0' * 64), 'SHA-256'),
            ('timestamp', lambda e: e.update(observed_at='2026-10-17T04:00:00'), 'UTC'),
            ('version', lambda e: e.update(version='SRC-OTHER'), 'version'),
        ]
        for name, mutate, message in mutations:
            with self.subTest(name=name):
                self.handoff = copy.deepcopy(original)
                mutate(self.handoff['files'][0])
                with self.assertRaisesRegex(s.SourceError, message):
                    self.prepare()
                self.assertEqual(list(self.run.iterdir()), [])

    def test_page_markers_and_required_card_fields_are_independent_of_assertions(self):
        from pypdf import PdfReader, PdfWriter
        original = self.handoff['files'][0]
        path = self.acq / original['path']
        reader = PdfReader(path)
        writer = PdfWriter()
        writer.add_page(reader.pages[0])
        with path.open('wb') as stream:
            writer.write(stream)
        original['sha256'] = s._hash(path)
        with self.assertRaisesRegex(s.SourceError, 'page coverage'):
            self.prepare()
        with self.assertRaisesRegex(s.SourceError, 'Missing card field'):
            s._receipt('Receipt reference: fake', 'receipts', 'synthetic')


if __name__ == '__main__':
    unittest.main()

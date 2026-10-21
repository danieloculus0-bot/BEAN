import tempfile
import unittest
from indexed_ledger import IndexedLedger, junit_events, linear_lookup

class LedgerTests(unittest.TestCase):
    def test_original_junit_exact(self):
        raw=b'<testsuite><testcase classname="A" name="x"/><testcase classname="A" name="y"><failure message="failed"/></testcase></testsuite>'
        with tempfile.TemporaryDirectory() as work:
            ledger=IndexedLedger(work)
            manifest=ledger.append('run1',junit_events(raw))
            self.assertEqual(ledger.rebuild(),3)
            self.assertEqual(ledger.original_junit('run1'),raw)
            self.assertEqual(ledger.scoreboard()['runs']['run1'],{'failed':1,'passed':1})
            for item in manifest['items']:
                self.assertEqual(ledger.get(item['id']),linear_lookup(ledger.archive/'run1.jsonl.gz',item['id']))
            ledger.cache.unlink()
            ledger.rebuild()
            self.assertEqual(ledger.original_junit('run1'),raw)


class AdversarialLedgerTests(unittest.TestCase):
    def test_modified_compressed_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            ledger=IndexedLedger(work)
            ledger.append('case1',[{'kind':'test','name':'A','status':'passed'}])
            ledger.rebuild()
            file=ledger.archive/'case1.jsonl.gz'
            bytes_=bytearray(file.read_bytes())
            bytes_[-4] ^= 1
            file.write_bytes(bytes_)
            with self.assertRaisesRegex(ValueError,'archive hash mismatch'):
                ledger.rebuild()

    def test_duplicate_names_are_two_real_events(self):
        with tempfile.TemporaryDirectory() as work:
            ledger=IndexedLedger(work)
            ledger.append('case2',[
                {'kind':'test','name':'same','status':'passed'},
                {'kind':'test','name':'same','status':'failed'}])
            ledger.rebuild()
            cases=[ledger.get(i)['status'] for i in ledger.ids(name='same')]
            self.assertEqual(cases,['passed','failed'])

    def test_missing_archive_is_detected(self):
        with tempfile.TemporaryDirectory() as work:
            ledger=IndexedLedger(work)
            ledger.append('case3',[{'kind':'test','name':'A','status':'passed'}])
            (ledger.archive/'case3.jsonl.gz').unlink()
            with self.assertRaisesRegex(ValueError,'orphaned archive'):
                ledger.rebuild()


if __name__=='__main__': unittest.main()

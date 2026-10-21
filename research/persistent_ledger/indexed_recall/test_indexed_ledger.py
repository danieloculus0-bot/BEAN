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

if __name__=='__main__': unittest.main()

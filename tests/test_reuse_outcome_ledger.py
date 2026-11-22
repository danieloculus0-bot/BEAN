"""Deterministic integrity tests for retained reuse evidence, not model learning."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bean.optimization.reuse_outcome_ledger import append_reuse_outcome, verify_reuse_outcomes


class ReuseOutcomeLedgerTests(unittest.TestCase):
    def test_records_success_and_failure_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "outcomes.sqlite"
            source = hashlib.sha256(b"skill").hexdigest()
            tests = hashlib.sha256(b"withheld").hexdigest()
            a = append_reuse_outcome(db, skill="sample", source_sha256=source,
                                     tests_sha256=tests, passed=False, novel_test_set=True)
            b = append_reuse_outcome(db, skill="sample", source_sha256=source,
                                     tests_sha256=tests, passed=True, novel_test_set=True)
            self.assertEqual(b["prior_sha256"], a["receipt_sha256"])
            self.assertEqual([x["passed"] for x in verify_reuse_outcomes(db)], [False, True])
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE reuse_outcomes SET payload=? WHERE sequence=1",
                                   ('{"passed":true}',))
            with self.assertRaises(ValueError):
                verify_reuse_outcomes(db)

    def test_rejects_invalid_identity_and_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                append_reuse_outcome(Path(directory) / "x.sqlite", skill="sample",
                                     source_sha256="bad", tests_sha256="0" * 64,
                                     passed=True, novel_test_set=True)
            with self.assertRaises(ValueError):
                append_reuse_outcome(Path(directory) / "x.sqlite", skill="sample",
                                     source_sha256="0" * 64, tests_sha256="0" * 64,
                                     passed=1, novel_test_set=True)


if __name__ == "__main__":
    unittest.main()

"""Deterministic integrity tests for retained reuse evidence, not model learning."""
import hashlib
import sqlite3
import json
import subprocess
import sys
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

    def test_fresh_process_verifies_failures_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "outcomes.sqlite"
            source = hashlib.sha256(b"model-generated-source").hexdigest()
            tests = hashlib.sha256(b"independent-holdout").hexdigest()
            append_reuse_outcome(db, skill="retained", source_sha256=source,
                                 tests_sha256=tests, passed=False, novel_test_set=True)
            command = [sys.executable, "-m", "bean.optimization.reuse_outcome_ledger", str(db)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout),
                             {"verified": True, "count": 1, "failures": 1})
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE reuse_outcomes SET payload=? WHERE sequence=1",
                                   ('{"passed":true}',))
            rejected = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("integrity verification failed", rejected.stderr)

    def test_pinned_checkpoint_detects_deleted_tail_across_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "outcomes.sqlite"
            source = hashlib.sha256(b"candidate").hexdigest()
            tests = hashlib.sha256(b"holdout").hexdigest()
            append_reuse_outcome(db, skill="retained", source_sha256=source,
                                 tests_sha256=tests, passed=False, novel_test_set=True)
            final = append_reuse_outcome(db, skill="retained", source_sha256=source,
                                         tests_sha256=tests, passed=True, novel_test_set=True)
            command = [sys.executable, "-m", "bean.optimization.reuse_outcome_ledger",
                       str(db), "--expected-count", "2",
                       "--expected-head-sha256", final["receipt_sha256"]]
            valid = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            with sqlite3.connect(db) as connection:
                connection.execute("DELETE FROM reuse_outcomes WHERE sequence=2")
            # The remaining chain is internally valid, but a pinned checkpoint
            # detects the lost successful evaluation receipt.
            self.assertEqual(len(verify_reuse_outcomes(db)), 1)
            rejected = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("checkpoint count mismatch", rejected.stderr)

    def test_export_checkpoint_then_verify_in_fresh_process(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "outcomes.sqlite"
            digest = hashlib.sha256(b"skill").hexdigest()
            append_reuse_outcome(db, skill="retained", source_sha256=digest,
                                 tests_sha256=digest, passed=False, novel_test_set=True)
            base = [sys.executable, "-m", "bean.optimization.reuse_outcome_ledger", str(db)]
            exported = subprocess.run(base + ["--emit-checkpoint"], capture_output=True,
                                      text=True, check=False)
            self.assertEqual(exported.returncode, 0, exported.stderr)
            checkpoint = json.loads(exported.stdout)
            self.assertEqual(checkpoint["count"], 1)
            self.assertEqual(len(checkpoint["head_sha256"]), 64)
            verified = subprocess.run(base + ["--expected-count", str(checkpoint["count"]),
                                              "--expected-head-sha256", checkpoint["head_sha256"]],
                                      capture_output=True, text=True, check=False)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            with sqlite3.connect(db) as connection:
                connection.execute("DELETE FROM reuse_outcomes")
            rejected = subprocess.run(base + ["--expected-count", str(checkpoint["count"]),
                                              "--expected-head-sha256", checkpoint["head_sha256"]],
                                      capture_output=True, text=True, check=False)
            self.assertNotEqual(rejected.returncode, 0)

    def test_control_arm_identity_survives_restart_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "outcomes.sqlite"
            digest = hashlib.sha256(b"same withheld task").hexdigest()
            for arm, passed in (("candidate", True), ("frozen", False),
                                ("no_memory", False), ("grammar_matched", True),
                                ("strong_control", True)):
                append_reuse_outcome(db, skill="transfer", source_sha256=digest,
                                     tests_sha256=digest, passed=passed,
                                     novel_test_set=True, experiment_id="holdout-001",
                                     condition=arm)
            cmd = [sys.executable, "-m", "bean.optimization.reuse_outcome_ledger",
                   str(db), "--expected-count", "5"]
            checked = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            outcomes = verify_reuse_outcomes(db)
            self.assertEqual([item["condition"] for item in outcomes],
                             ["candidate", "frozen", "no_memory", "grammar_matched", "strong_control"])
            self.assertTrue(all(item["experiment_id"] == "holdout-001" for item in outcomes))
            with sqlite3.connect(db) as connection:
                connection.execute("UPDATE reuse_outcomes SET payload=replace(payload, ?, ?) WHERE sequence=2",
                                   ('"frozen"', '"candidate"'))
            rejected = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertNotEqual(rejected.returncode, 0)

    def test_rejects_unregistered_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                append_reuse_outcome(Path(directory) / "x.sqlite", skill="sample",
                                     source_sha256="0" * 64, tests_sha256="0" * 64,
                                     passed=True, novel_test_set=True,
                                     condition="uncontrolled")
            with self.assertRaises(ValueError):
                append_reuse_outcome(Path(directory) / "x.sqlite", skill="sample",
                                     source_sha256="0" * 64, tests_sha256="0" * 64,
                                     passed=True, novel_test_set=True,
                                     experiment_id="")

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

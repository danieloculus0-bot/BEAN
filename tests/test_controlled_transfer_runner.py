"""Regression for the executable five-arm transfer runner (synthetic, not learning)."""
import json
import hashlib
import sqlite3
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

from bean.optimization.controlled_transfer_runner import run_manifest
from bean.optimization.reuse_outcome_ledger import verify_reuse_outcomes


class ControlledTransferRunnerTests(unittest.TestCase):
    def test_five_arms_persist_across_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.py").write_text("def twice(x): return x * 2\n")
            (root / "bad.py").write_text("def twice(x): return x + 2\n")
            (root / "test.py").write_text(
                "import runpy,sys\n"
                "skill=runpy.run_path(sys.argv[1])\n"
                "assert skill['twice'](7)==14\n"
            )
            arms = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")
            spec = {"experiment_id": "synthetic-control-regression", "model_id": "none",
                    "seed": 19, "timeout_seconds": 5,
                    "tasks": [{"skill": "twice", "tests": "test.py",
                               "novel_test_set": False,
                               "sources": {arm: ("good.py" if arm == "candidate" else "bad.py")
                                           for arm in arms}}]}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(spec))
            db = root / "receipts.sqlite"
            result = run_manifest(manifest, db)
            self.assertEqual(len(result["receipts"]), 5)
            self.assertEqual(result["summary"]["matched_tasks"], 0)
            self.assertEqual(len(result["summary"]["excluded"]), 1)
            self.assertIn("not_marked_novel", result["summary"]["excluded"][0]["reasons"])
            self.assertEqual(result["summary"]["correct"]["candidate"], 0)
            self.assertFalse(result["independent_learning_verified"])
            self.assertTrue(result["separate_process_ledger_verified"])
            self.assertEqual(len(verify_reuse_outcomes(db)), 5)
            self.assertEqual(set(x["condition"] for x in result["receipts"]), set(arms))
            self.assertNotEqual([x["condition"] for x in result["receipts"]], list(arms))
            # Reusing an experiment ID would blend old and new outcomes.
            # Reject it before any new receipts are appended.
            with self.assertRaisesRegex(ValueError, "experiment_id already exists"):
                run_manifest(manifest, db)
            self.assertEqual(len(verify_reuse_outcomes(db)), 5)

    def test_restart_rejects_same_identity_with_changed_outcome(self):
        # A valid-looking child response with matching arm identities but
        # altered payload digests must not certify recovered evidence.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.py").write_text("def twice(x): return x * 2\n")
            (root / "test.py").write_text(
                "import runpy,sys\n"
                "assert runpy.run_path(sys.argv[1])['twice'](7)==14\n"
            )
            arms = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "experiment_id": "restart-tamper", "model_id": "none", "seed": 1,
                "tasks": [{"skill": "twice", "tests": "test.py",
                           "sources": {arm: "good.py" for arm in arms}}],
            }))
            db = root / "receipts.sqlite"
            # Simulate a separate interpreter returning different full
            # payload digests despite the same five persisted arm identities.
            with patch("bean.optimization.controlled_transfer_runner.subprocess.run",
                       return_value=CompletedProcess([], 0, '["altered"]', "")):
                with self.assertRaisesRegex(RuntimeError, "verification mismatch"):
                    run_manifest(manifest, db)
            self.assertEqual(len(verify_reuse_outcomes(db)), 5)

    def test_rechained_ledger_cannot_replace_arm_receipts(self):
        # A modified outcome with a freshly valid SHA chain must not be
        # accepted as the original observed result after interpreter restart.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("def twice(x): return x * 2\\n")
            (root / "test.py").write_text(
                "import runpy,sys\\n"
                "assert runpy.run_path(sys.argv[1])['twice'](7)==14\\n"
            )
            arms = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "experiment_id": "rechain", "model_id": "none", "seed": 9,
                "tasks": [{"skill": "twice", "tests": "test.py",
                           "sources": {arm: "source.py" for arm in arms}}],
            }))
            db = root / "receipts.sqlite"
            original_run = subprocess.run
            mutated = []

            def mutate_before_restart(argv, **kwargs):
                if len(argv) > 1 and argv[1] == "-c":
                    with sqlite3.connect(db) as conn:
                        rows = conn.execute(
                            "SELECT sequence,payload FROM reuse_outcomes ORDER BY sequence"
                        ).fetchall()
                        prior = "0" * 64
                        for index, (sequence, encoded) in enumerate(rows):
                            payload = json.loads(encoded)
                            if index == 0:
                                payload["passed"] = not payload["passed"]
                            encoded = json.dumps(
                                payload, sort_keys=True, separators=(",", ":"), allow_nan=False
                            )
                            digest = hashlib.sha256(
                                prior.encode("ascii") + encoded.encode("utf-8")
                            ).hexdigest()
                            conn.execute(
                                "UPDATE reuse_outcomes SET payload=?,prior_sha256=?,"
                                "receipt_sha256=? WHERE sequence=?",
                                (encoded, prior, digest, sequence),
                            )
                            prior = digest
                    mutated.append(True)
                return original_run(argv, **kwargs)

            with patch("bean.optimization.controlled_transfer_runner.subprocess.run",
                       side_effect=mutate_before_restart):
                with self.assertRaisesRegex(RuntimeError, "verification mismatch"):
                    run_manifest(manifest, db)
            self.assertTrue(mutated)
            self.assertEqual(len(verify_reuse_outcomes(db)), 5)

    def test_mutating_holdout_aborts_before_other_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("pass\n")
            test = root / "test.py"
            test.write_text(
                "from pathlib import Path\n"
                "p=Path(__file__)\n"
                "p.write_text(p.read_text()+chr(35)+chr(32)+chr(97))\n"
            )
            arms = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "experiment_id": "drift", "model_id": "none", "seed": 2,
                "tasks": [{"skill": "mutator", "tests": "test.py",
                           "sources": {arm: "source.py" for arm in arms}}],
            }))
            db = root / "receipts.sqlite"
            with self.assertRaisesRegex(ValueError, "input drift"):
                run_manifest(manifest, db)
            # The first observed attempt is retained, but subsequent arms
            # must not consume the mutated test file.
            self.assertEqual(len(verify_reuse_outcomes(db)), 1)

    def test_duplicate_skill_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("pass\n")
            (root / "test.py").write_text("pass\n")
            arms = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")
            task = {"skill": "repeated", "tests": "test.py",
                    "sources": {arm: "source.py" for arm in arms}}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "experiment_id": "duplicate", "model_id": "none", "seed": 19,
                "tasks": [task, task],
            }))
            db = root / "receipts.sqlite"
            with self.assertRaisesRegex(ValueError, "duplicate skill"):
                run_manifest(manifest, db)
            self.assertFalse(db.exists())

    def test_incomplete_manifest_never_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test.py").write_text("pass\n")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "experiment_id": "invalid", "model_id": "none", "seed": 0,
                "tasks": [{"skill": "x", "tests": "test.py", "sources": {"candidate": "missing.py"}}],
            }))
            db = root / "receipts.sqlite"
            with self.assertRaises(ValueError):
                run_manifest(manifest, db)
            self.assertFalse(db.exists())


if __name__ == "__main__":
    unittest.main()

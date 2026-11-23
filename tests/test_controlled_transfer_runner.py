"""Regression for the executable five-arm transfer runner (synthetic, not learning)."""
import json
from pathlib import Path
import tempfile
import unittest

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
                               "novel_test_set": True,
                               "sources": {arm: ("good.py" if arm == "candidate" else "bad.py")
                                           for arm in arms}}]}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(spec))
            db = root / "receipts.sqlite"
            result = run_manifest(manifest, db)
            self.assertEqual(len(result["receipts"]), 5)
            self.assertEqual(result["summary"]["matched_tasks"], 1)
            self.assertEqual(result["summary"]["correct"]["candidate"], 1)
            self.assertFalse(result["independent_learning_verified"])
            self.assertEqual(len(verify_reuse_outcomes(db)), 5)

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

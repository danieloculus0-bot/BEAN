"""Matched-arm summaries are descriptive; these fixtures are synthetic."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bean.optimization.reuse_outcome_ledger import (
    append_reuse_outcome, summarize_matched_experiment, verify_reuse_outcomes,
)

ARMS = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")


class MatchedSummaryTests(unittest.TestCase):
    def test_complete_paired_summary_in_fresh_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "ledger.sqlite"
            for task, answers in (
                ("novel-one", (True, False, False, True, True)),
                ("novel-two", (False, True, False, True, True)),
            ):
                test_sha = hashlib.sha256(task.encode()).hexdigest()
                for arm, passed in zip(ARMS, answers):
                    source_sha = hashlib.sha256(arm.encode()).hexdigest()
                    append_reuse_outcome(
                        db, skill="transfer", source_sha256=source_sha,
                        tests_sha256=test_sha, passed=passed,
                        novel_test_set=True, experiment_id="exp-1", condition=arm,
                        model_id="qwen-local", evaluation_budget=100, seed=42,
                    )
            command = [sys.executable, "-m", "bean.optimization.reuse_outcome_ledger",
                       str(db), "--summarize-experiment", "exp-1"]
            proc = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = json.loads(proc.stdout)["matched_summary"]
            self.assertEqual(summary["matched_tasks"], 2)
            self.assertEqual(summary["correct"]["candidate"], 1)
            self.assertEqual(summary["correct"]["strong_control"], 2)
            self.assertEqual(summary["candidate_minus_controls"]["strong_control"], -1)
            self.assertFalse(summary["independent_learning_verified"])
            self.assertTrue(summary["equal_budget_verified"])

    def test_incomplete_and_duplicate_arms_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "ledger.sqlite"
            digest = hashlib.sha256(b"holdout").hexdigest()
            for arm in ("candidate", "candidate", "frozen"):
                append_reuse_outcome(
                    db, skill="sample", source_sha256=digest, tests_sha256=digest,
                    passed=True, novel_test_set=True, experiment_id="exp-2",
                    condition=arm,
                )
            summary = summarize_matched_experiment(verify_reuse_outcomes(db), "exp-2")
            self.assertEqual(summary["matched_tasks"], 0)
            self.assertEqual(summary["correct"]["candidate"], 0)
            self.assertEqual(summary["excluded"][0]["reasons"],
                             ["duplicate_or_unknown_arm", "incomplete_arms"])

    def test_mismatched_budget_and_legacy_receipts_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "ledger.sqlite"
            digest = hashlib.sha256(b"task").hexdigest()
            for arm in ARMS:
                append_reuse_outcome(
                    db, skill="transfer", source_sha256=digest, tests_sha256=digest,
                    passed=True, novel_test_set=True, experiment_id="exp-budget",
                    condition=arm, model_id="local", evaluation_budget=100 if arm != "frozen" else 200,
                    seed=7,
                )
            result = summarize_matched_experiment(verify_reuse_outcomes(db), "exp-budget")
            self.assertEqual(result["matched_tasks"], 0)
            self.assertIn("mismatched_evaluation_budget", result["excluded"][0]["reasons"])
            self.assertFalse(result["equal_budget_verified"])

    def test_no_matching_receipts_never_imply_superiority(self):
        result = summarize_matched_experiment([], "missing")
        self.assertEqual(result["matched_tasks"], 0)
        self.assertEqual(result["candidate_minus_controls"]["strong_control"], 0)
        self.assertFalse(result["independent_learning_verified"])


if __name__ == "__main__":
    unittest.main()

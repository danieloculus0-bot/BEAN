"""Synthetic subprocess checks for the native retained-skill evaluation adapter."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from bean.optimization.metered_reuse_evaluator import evaluate_and_record, evaluate_python_skill
from bean.optimization.reuse_outcome_ledger import verify_reuse_outcomes


class MeteredEvaluatorTests(unittest.TestCase):
    def test_pass_and_failure_persist_in_same_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            tests = root / "holdout.py"
            source.write_text("answer = 7\n", encoding="utf-8")
            tests.write_text("assert 7 == 7\n", encoding="utf-8")
            database = root / "outcomes.sqlite"
            common = dict(
                database=database, skill="synthetic-eval", source_file=source,
                tests_file=tests, experiment_id="metered-smoke", model_id="none",
                seed=19, timeout_seconds=5,
            )
            good = evaluate_and_record(
                **common, condition="candidate",
                argv=[sys.executable, "-c", "import sys; sys.exit(0)"],
            )
            bad = evaluate_and_record(
                **common, condition="frozen",
                argv=[sys.executable, "-c", "import sys; sys.exit(3)"],
            )
            self.assertTrue(good["passed"])
            self.assertFalse(bad["passed"])
            self.assertEqual(bad["returncode"], 3)
            self.assertFalse(good["provider_invoked"])
            self.assertFalse(good["semantic_correctness_verified"])
            self.assertEqual(good["timeout_budget_ms"], 5000)
            self.assertEqual(good["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            outcomes = verify_reuse_outcomes(database)
            self.assertEqual([r["passed"] for r in outcomes], [True, False])
            self.assertEqual([r["condition"] for r in outcomes], ["candidate", "frozen"])
            self.assertEqual(outcomes[0]["evaluation_budget"], 5000)
            self.assertFalse(outcomes[0]["novel_test_set"])
            self.assertFalse(good["novel_test_set"])

    def test_explicit_novelty_and_invalid_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_text("pass\n", encoding="utf-8")
            database = root / "ledger.sqlite"
            common = dict(
                database=database, skill="attested-holdout", source_file=source,
                tests_file=source, argv=[sys.executable, "-c", "pass"],
                experiment_id="attestation", condition="candidate",
                model_id="none", seed=4,
            )
            with self.assertRaises(ValueError):
                evaluate_and_record(**common, novel_test_set="true")
            self.assertFalse(database.exists())
            observed = evaluate_and_record(**common, novel_test_set=True)
            self.assertTrue(observed["novel_test_set"])
            self.assertTrue(verify_reuse_outcomes(database)[0]["novel_test_set"])

    def test_timeout_retained_as_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_text("pass\n", encoding="utf-8")
            result = evaluate_and_record(
                root / "ledger.sqlite", skill="timeout", source_file=source,
                tests_file=source, argv=[sys.executable, "-c", "import time; time.sleep(2)"],
                experiment_id="timeout-smoke", condition="candidate",
                model_id="none", seed=0, timeout_seconds=0.05,
            )
            self.assertTrue(result["timed_out"])
            self.assertFalse(result["passed"])
            self.assertEqual(len(verify_reuse_outcomes(root / "ledger.sqlite")), 1)

    def test_invalid_command_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_text("pass\n", encoding="utf-8")
            database = root / "ledger.sqlite"
            with self.assertRaises(ValueError):
                evaluate_and_record(
                    database, skill="bad", source_file=source, tests_file=source,
                    argv=[], experiment_id="bad", condition="candidate",
                    model_id="none", seed=0,
                )
            self.assertFalse(database.exists())


    def test_direct_python_skill_runs_real_tests_in_fresh_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "skill.py"
            tests = root / "withheld.py"
            database = root / "results.sqlite"
            source.write_text("def double(x): return x * 2\n", encoding="utf-8")
            tests.write_text(
                "import runpy, sys\n"
                "skill = runpy.run_path(sys.argv[1])\n"
                "assert skill['double'](11) == 22\n", encoding="utf-8"
            )
            common = dict(database=database, skill="direct-python",
                          source_file=source, tests_file=tests,
                          experiment_id="direct-python-regression",
                          model_id="none", seed=1, timeout_seconds=5)
            passed = evaluate_python_skill(**common, condition="candidate")
            self.assertTrue(passed["passed"], passed)
            source.write_text("def double(x): return x + 2\n", encoding="utf-8")
            failed = evaluate_python_skill(**common, condition="frozen")
            self.assertFalse(failed["passed"])
            self.assertNotEqual(failed["returncode"], 0)
            self.assertEqual([r["passed"] for r in verify_reuse_outcomes(database)],
                             [True, False])
            with self.assertRaises(ValueError):
                evaluate_python_skill(**{**common, "tests_file": source},
                                      condition="candidate")


if __name__ == "__main__":
    unittest.main()

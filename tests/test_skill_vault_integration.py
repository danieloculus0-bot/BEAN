"""End-to-end Lab019 skill incubation, promotion and fresh-process reuse."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bean.optimization.skill_incubator import incubate_skill
from bean.optimization.skill_vault import promote, retrieve, reuse


class Writer:
    calls = 0

    def propose(self, task, original, history, iteration):
        self.calls += 1
        return "def solve(value):\n    return value * 2\n".replace("\n", "\n")


class SkillVaultIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.training = self.fixture("training", 3)
        self.holdout = self.fixture("holdout", 11)
        self.reuse_project = self.fixture("reuse", 29)
        self.output = self.root / "output"
        self.journal = self.root / "journal.sqlite3"
        self.vault = self.root / "vault"

    def fixture(self, name, number):
        root = self.root / name
        (root / "bean" / "skills").mkdir(parents=True)
        (root / "bean" / "__init__.py").write_text("")
        (root / "bean" / "skills" / "__init__.py").write_text("")
        (root / "tests").mkdir()
        (root / "tests" / "test_case.py").write_text(
            "import unittest\nfrom bean.skills.double_value import solve\n"
            "class TestCase(unittest.TestCase):\n"
            "    def test_value(self):\n"
            "        self.assertEqual(solve(" + str(number) + "), " + str(number * 2) + ")\n")
        return root

    def build(self):
        writer = Writer()
        report = incubate_skill(
            project=self.training, holdout_project=self.holdout,
            name="double_value", task="Create a reusable integer doubling function",
            journal_path=self.journal, output=self.output,
            provider=writer, attempts=2)
        self.assertEqual(writer.calls, 1)
        self.assertTrue(report["skill_promotion_ready"])
        return report

    def test_promote_restart_reuse_new_holdout(self):
        report = self.build()
        receipt = promote(report=report, output=self.output,
                          journal_path=self.journal, vault=self.vault)
        self.assertEqual(receipt["source_sha256"], report["accepted_source"])
        # A different interpreter proves the skill is retained on disk.
        process = subprocess.run(
            [sys.executable, "-m", "bean.optimization.skill_vault", "reuse",
             "--vault", str(self.vault), "--name", "double_value",
             "--project", str(self.reuse_project)],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])})
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        result = json.loads(process.stdout)
        self.assertTrue(result["passed"])
        self.assertTrue(result["independent_from_promotion_holdout"])
        self.assertFalse(result["provider_invoked"])
        self.assertEqual(result["result"]["test_count"], 1)

    def test_reject_unverified_and_tampered_source(self):
        report = self.build()
        bad = dict(report, independent_holdout_verified=False)
        with self.assertRaises(ValueError):
            promote(report=bad, output=self.output,
                    journal_path=self.journal, vault=self.vault)
        promote(report=report, output=self.output,
                journal_path=self.journal, vault=self.vault)
        (self.vault / "double_value" / "skill.py").write_text("def solve(v): return 0\n")
        with self.assertRaises(ValueError):
            retrieve(vault=self.vault, name="double_value")

    def test_no_duplicate_promotion(self):
        report = self.build()
        promote(report=report, output=self.output,
                journal_path=self.journal, vault=self.vault)
        with self.assertRaises(FileExistsError):
            promote(report=report, output=self.output,
                    journal_path=self.journal, vault=self.vault)


if __name__ == "__main__":
    unittest.main()

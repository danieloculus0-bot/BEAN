"""Actual branch-only mechanisms; MOCK trials are never evidence of learning."""
import json
from pathlib import Path
import tempfile
import unittest

from bean.learning.experimental import (
    Lesson, TrialCase, ExperienceBank, assess_nodes, material_for, run_paired_trial,
)


class RuleFixture:
    model_id = "rule-fixture-0"
    provider_kind = "synthetic_fixture"
    def complete(self, question, context):
        # Synthetic rule is intentionally simplistic and openly labeled.
        if "SORT_ASC" in context and question.startswith("sort "):
            return ",".join(sorted(question[5:].split(",")))
        return "unknown"


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "journal.sqlite"

    def test_identity_and_all_node_dependencies_reviewed(self):
        nodes = assess_nodes()
        self.assertEqual(len(nodes), 7)
        self.assertTrue(all(x["origin_values_unchanged"] for x in nodes))
        self.assertEqual(next(n for n in nodes if n["node"] == "weights")["viability"],
                         "research_only")
        self.assertFalse(any(x["learning_improvement_verified"] for x in nodes))

    def test_journal_persists_across_restart_and_rejects_tampering(self):
        bank = ExperienceBank(self.db)
        bank.add(Lesson("lesson1", "reflection", "sorting", "SORT_ASC",
                        ("fake-evaluation:fixture1",), "Observed mock failure"))
        self.assertEqual(material_for(bank, "reflection", "sorting"), "SORT_ASC")
        bank.close()
        restored = ExperienceBank(self.db)
        self.assertEqual(len(restored.lessons(domain="sorting")), 1)
        with self.assertRaises(ValueError):
            restored.add(Lesson("lesson1", "reflection", "sorting", "duplicate",
                                ("ref:2",), "observed"))
        restored.close()
        import sqlite3
        db = sqlite3.connect(str(self.db))
        record = db.execute("select payload from attempts limit 1").fetchone()[0]
        db.execute("update attempts set payload=? where id=1",
                   (record.replace("SORT_ASC", "SORT_DESC"),))
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            ExperienceBank(self.db)

    def test_matched_synthetic_trial_and_unchanged_model_identity(self):
        bank = ExperienceBank(self.db)
        bank.add(Lesson("sorting-rule", "reflection", "sorting", "SORT_ASC",
                        ("synthetic:observation:1",), "First attempt failed"))
        bank.add(Lesson("unrelated", "reflection", "welding", "IGNORE_WELDS",
                        ("synthetic:observation:2",), "Other domain"))
        cases = [TrialCase("case1", "sorting", "sort z,a", "a,z"),
                 TrialCase("case2", "sorting", "sort b,a", "a,b")]
        report = run_paired_trial(bank=bank, cases=cases, model=RuleFixture(),
                                  judge=lambda expected, answer: expected == answer,
                                  arms=("cold","reflection","placebo"), replicates=2)
        self.assertEqual(report["scores"], {"cold":0,"reflection":4,"placebo":0})
        self.assertEqual(report["verdict"], "synthetic_fixture_not_learning_proof")
        self.assertFalse(report["model_weights_modified"])
        self.assertFalse(report["independent_evaluation_authenticated"])
        self.assertEqual(len({x["task_id"] for x in report["records"]}),2)
        bank.close()
        bank=ExperienceBank(self.db)
        self.assertEqual(len(bank.journal.events()),3)
        bank.close()

    def test_no_fabricated_source_or_evaluator_confidence(self):
        bank=ExperienceBank(self.db)
        with self.assertRaises(ValueError):
            bank.add(Lesson("x","reflection","a","rule",(),"failure"))
        with self.assertRaises(TypeError):
            run_paired_trial(bank=bank,
              cases=[TrialCase("a","a","a","a")],model=RuleFixture(),
              judge=lambda a,b:1)
        with self.assertRaises(ValueError):
            run_paired_trial(bank=bank,
              cases=[TrialCase("a","a","a","a")],model=RuleFixture(),
              judge=lambda a,b:True,arms=("cold","cold"))
        bank.close()


if __name__ == "__main__":
    unittest.main()

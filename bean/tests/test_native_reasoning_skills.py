"""Tests the real BEAN Lab026 journal and strategy selector, not a mock brain."""
import tempfile
import unittest
from pathlib import Path
from bean.learning import BEANReasoningSkills, ExperienceBank


class NativeReasoningSkillsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "skills.sqlite"
        self.bank = ExperienceBank(self.path)
        self.addCleanup(self.bank.close)
        self.skills = BEANReasoningSkills(self.bank)

    def seed(self):
        self.skills.reflect(
            domain="sorting", task_id="dev-1",
            observed="reversed alphabetical tokens",
            expected="alphabetical tokens",
            adjustment_hypothesis="sort tokens alphabetically",
            evidence_refs=["fixture:dev-1"])
        self.skills.retain_skill(
            domain="sorting", name="alphabetical order",
            steps=["split tokens", "sort alphabetically", "join tokens"],
            passed=True, evidence_refs=["fixture:skill"])
        self.skills.propose_instruction(
            domain="sorting", instruction="sort alphabetical tokens",
            evidence_refs=["fixture:prompt"])
        self.skills.reflect(
            domain="welding", task_id="dev-other",
            observed="rough weld bead", expected="uniform weld bead",
            adjustment_hypothesis="adjust welding travel speed",
            evidence_refs=["fixture:other"])

    @staticmethod
    def outcomes(winner="reflection"):
        return [
            {"task_id": task, "arm": arm, "replicate": 0,
             "passed": arm == winner,
             "evidence_ref": "fixture:" + task + ":" + arm}
            for task in ("selection-A", "selection-B")
            for arm in ("cold", "reflection", "skill", "prompt", "placebo")
        ]

    def test_evidence_retrieval_is_ranked_domain_bound_and_no_invention(self):
        self.seed()
        results = self.skills.recall(
            domain="sorting", query="alphabetical tokens", limit=2)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(x["matched_terms"] for x in results))
        self.assertTrue(all(x["evidence_refs"] for x in results))
        self.assertTrue(all(x["domain"] == "sorting" for x in results))
        self.assertEqual(self.skills.recall(domain="sorting", query="zebra"), [])
        with self.assertRaises(ValueError):
            self.skills.recall(domain="sorting", query="tokens", limit=0)

    def test_reflection_marks_unverified_hypothesis_and_deduplicates(self):
        args = dict(domain="drawings", task_id="drawing-1",
                    observed="wrong tolerance", expected="correct tolerance",
                    adjustment_hypothesis="associate tolerance with local dimension",
                    evidence_refs=["fixture:drawing-1"])
        first = self.skills.reflect(**args)
        count = len(self.bank.journal.events())
        duplicate = self.skills.reflect(**args)
        self.assertTrue(first["new"])
        self.assertFalse(duplicate["new"])
        self.assertEqual(len(self.bank.journal.events()), count)
        self.assertIn("unverified adjustment hypothesis", self.bank.lessons()[0].text)
        with self.assertRaises(ValueError):
            self.skills.reflect(domain="x", task_id="t",
                                observed="same", expected="same",
                                adjustment_hypothesis="fix",
                                evidence_refs=["fixture"])

    def test_skill_requires_positive_host_receipt(self):
        with self.assertRaises(ValueError):
            self.skills.retain_skill(domain="x", name="fix", steps=["step"],
                                     passed=False, evidence_refs=["fixture"])
        self.assertEqual(self.bank.lessons(), [])
        self.skills.retain_skill(domain="x", name="fix",
                                 steps=["inspect", "correct"],
                                 passed=True, evidence_refs=["fixture"])
        self.assertIn("2. correct", self.bank.lessons()[0].text)

    def test_prompt_is_candidate_not_verified_learning(self):
        self.skills.propose_instruction(
            domain="sorting", instruction="recheck each token",
            evidence_refs=["fixture:proposal"])
        self.assertEqual(self.bank.lessons()[0].observed_outcome,
                         "unevaluated_instruction_candidate")

    def test_strategy_reuses_native_selector_and_survives_restart(self):
        self.seed()
        choice = self.skills.select_strategy(
            domain="sorting", rows=self.outcomes(),
            evaluator_id="test-host", dataset_id="selection-only-v1")
        self.assertEqual(choice["arm"], "reflection")
        packet = self.skills.decide(
            domain="sorting", task_ref="new-task", query="alphabetical tokens")
        self.assertEqual(packet["selected_strategy"], "reflection")
        self.assertEqual(len(packet["lessons"]), 1)
        self.assertFalse(packet["model_invoked"])
        self.assertIn("fixture:dev-1", packet["lessons"][0]["evidence_refs"])
        self.assertEqual(self.skills.present(
            domain="sorting", task_ref="new-task", query="tokens")["mode"],
            "render_only")
        self.bank.close()
        restored = ExperienceBank(self.path)
        try:
            packet2 = BEANReasoningSkills(restored).decide(
                domain="sorting", task_ref="after-restart",
                query="alphabetical tokens")
            self.assertEqual(packet2["lessons"], packet["lessons"])
            self.assertEqual(packet2["selected_strategy"], "reflection")
        finally:
            restored.close()

    def test_cold_policy_when_no_candidate_wins(self):
        self.seed()
        choice = self.skills.select_strategy(
            domain="sorting", rows=self.outcomes("cold"),
            evaluator_id="test-host", dataset_id="selection-cold")
        self.assertEqual(choice["arm"], "cold")
        self.assertEqual(self.skills.decide(
            domain="sorting", task_ref="task", query="alphabetical tokens")["lessons"], [])

    def test_incomplete_control_pairs_rejected_without_writing(self):
        self.seed()
        count = len(self.bank.journal.events())
        with self.assertRaises(ValueError):
            self.skills.select_strategy(
                domain="sorting", rows=self.outcomes()[:-1],
                evaluator_id="test-host", dataset_id="bad-selection")
        self.assertEqual(len(self.bank.journal.events()), count)

    def test_no_decision_before_measured_selection(self):
        self.seed()
        with self.assertRaises(ValueError):
            self.skills.decide(domain="sorting", task_ref="new", query="tokens")


if __name__ == "__main__":
    unittest.main()

"""Research -> real Bridge verification -> same BEAN feedback ledger -> replay.

The internet and model are synthetic fixtures; the Bridge library and native
BEAN reasoning/selector/feedback/journal implementations are real.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bean.learning import NativeReasoningService, TrialCase
from bean.learning.bridge_feedback import BridgeReasoningLoop
from bean.research import PublicWebSources, WebResearchService
from bean.tests.test_native_web_research import FakeInternet, ReasoningFixture, resolver


class HostVerifierFixture:
    def check(self, concept, observation):
        return (observation.ref.startswith("fixture:source:") and
                observation.value == "GREEN")


class FullResearchFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store = root / "bean-owned.sqlite3"
        self.core = NativeReasoningService(self.store, model=ReasoningFixture())
        self.addCleanup(self.core.close)
        self.internet = FakeInternet()
        self.sources = PublicWebSources(
            brave_key="fixture-only", request_fn=self.internet, resolver=resolver)
        self.research = WebResearchService(self.core, sources=self.sources)
        self.bridge = BridgeReasoningLoop(
            self.core, root / "bridge-definitions.sqlite",
            verifier=HostVerifierFixture())
        self.core.reflect(
            domain="inspection", task_id="existing-rule-1",
            observed="uncertain", expected="use source",
            adjustment_hypothesis="For inspection check an approved source",
            evidence_refs=["fixture:old-policy"])
        self.core.propose_instruction(
            domain="inspection", instruction="Check an approved source",
            evidence_refs=["fixture:old-prompt"])
        self.core.retain_skill(
            domain="inspection", name="check manual",
            steps=["Use a documented manual"], passed=True,
            evidence_refs=["fixture:old-skill"])
        results = [
            {"task_id": task, "arm": arm, "replicate": 0,
             "passed": arm == "reflection", "evidence_ref": task + ":" + arm}
            for task in ("train-1", "train-2")
            for arm in ("cold", "placebo", "reflection", "skill", "prompt")]
        winner = self.core.choose_from_outcomes(
            domain="inspection", rows=results,
            evaluator_id="fixture-judge", dataset_id="fixture-development")
        self.assertEqual(winner["arm"], "reflection")

    @staticmethod
    def observations(suffix=""):
        return [
            {"ref": "fixture:source:alpha" + suffix,
             "origin": "university-lab", "value": "GREEN"},
            {"ref": "fixture:source:beta" + suffix,
             "origin": "independent-supplier", "value": "GREEN"},
        ]

    def web_task(self, task_ref, question):
        return self.research.investigate(
            domain="inspection", task_ref=task_ref,
            question=question, provider="brave", max_pages=2)

    def test_evidence_research_then_bridge_feedback_uses_same_model_answer(self):
        question = "target inspection for sensor_a"
        first = self.web_task("web-1", question)
        self.assertEqual(first["answer"], "RED")
        calls = len(self.core.model.calls)
        verified = self.bridge.attempt(
            domain="inspection", task_ref="web-1", query=question,
            concept="sensor_a", as_of="2026-10-25T17:00:00Z",
            observations=self.observations(),
            existing_receipt=first["inference_receipt"])
        self.assertEqual(len(self.core.model.calls), calls)  # no redundant model call
        self.assertTrue(verified["feedback_applied"])
        self.assertFalse(verified["matched"])
        self.assertTrue(verified["correction_added"])
        self.assertEqual(self.core.status()["feedback_receipts"], 1)
        self.assertEqual(self.core.status()["research_evidence_packets"], 1)
        self.assertEqual(self.core.status()["selected_strategies"], 1)

        # New question. Same reasoning model, same saved strategy, new lesson.
        second_question = "target inspection for sensor_a NEW SAMPLE"
        second = self.web_task("web-2", second_question)
        self.assertEqual(second["answer"], "GREEN")
        self.assertEqual(second["strategy"], "reflection")

        # The different item must not inherit a sensor-specific factual claim.
        other = self.web_task("web-other", "target inspection for sensor_b")
        self.assertEqual(other["answer"], "RED")

        self.core.close()
        restored = NativeReasoningService(self.store, model=ReasoningFixture())
        try:
            holdout = restored.evaluate_holdout(
                domain="inspection",
                cases=[
                    TrialCase("h-a", "inspection",
                              "target inspection for sensor_a lot 101", "GREEN"),
                    TrialCase("h-b", "inspection",
                              "target inspection for sensor_a lot 102", "GREEN"),
                ],
                model=restored.model,
                judge=lambda expected, answer: expected == answer)
            self.assertEqual(holdout["trial"]["scores"],
                             {"cold": 0, "placebo": 0, "adaptive": 2})
            self.assertEqual(restored.status()["research_evidence_packets"], 3)
            self.assertEqual(restored.status()["feedback_receipts"], 1)
        finally:
            restored.close()

    def test_unverified_or_cross_task_receipts_cannot_promote_false_learning(self):
        before = self.web_task("id-1", "target inspection for sensor_d")
        duplicate_origin = [
            {"ref": "fixture:source:first", "origin": "same-source", "value": "GREEN"},
            {"ref": "fixture:source:second", "origin": "same-source", "value": "GREEN"},
        ]
        out = self.bridge.attempt(
            domain="inspection", task_ref="id-1",
            query="target inspection for sensor_d",
            concept="sensor_d", as_of="2026-10-25T17:00:00Z",
            observations=duplicate_origin,
            existing_receipt=before["inference_receipt"])
        self.assertFalse(out["feedback_applied"])
        self.assertEqual(self.core.status()["feedback_receipts"], 0)
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.bridge.attempt(
                domain="inspection", task_ref="wrong-id",
                query="target inspection for sensor_d",
                concept="sensor_d", as_of="2026-10-25T17:00:00Z",
                observations=self.observations(),
                existing_receipt=before["inference_receipt"])


if __name__ == "__main__":
    unittest.main()

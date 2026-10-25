"""Actually execute Bridge LAB009 investigations and BEAN Core policy feedback.

These models and evidence sources are explicitly deterministic synthetic test
fixtures. The tests establish *wiring*, trusted-logic boundaries and retention;
they do not imply a reasoning-model learned language or independent factual truth.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from bean.learning import NativeReasoningService, TrialCase
from bean.learning.bridge_feedback import (
    BridgeReasoningLoop, register_bridge_feedback_handler)
from bean.learning.experimental import material_for
# Bridge is an optional checkout in the Core-only CI matrix. When it is
# installed, execute these tests normally; otherwise record an explicit skip
# instead of failing unrelated Core test collection on an absent dependency.
try:
    from ezbean.learning_loop import SourceObservation
except ModuleNotFoundError as exc:
    if exc.name != "ezbean":
        raise
    raise unittest.SkipTest("BEAN-AI-Bridge optional package ezbean not installed") from exc


class ExperimentalModel:
    provider_kind = "synthetic_fixture"
    model_id = "branch-fixture-model-v1"

    def __init__(self):
        self.calls = []

    def complete(self, question, context):
        self.calls.append({"question": question, "context": context})
        if "SENSOR" in question:
            return "GREEN" if "GREEN" in context and "SENSOR" in context else "RED"
        if question.startswith("CALIBRATE"):
            return "PASS" if "APPROVED_RULE" in context else "FAIL"
        return "UNKNOWN"


class SourceVerifier:
    """Simulated source check, not a proxy for real-world authentication."""
    def check(self, concept, observation):
        return (observation.ref.startswith("fixture:trusted:")
                and observation.value == "GREEN")


class SimpleInbox:
    def __init__(self):
        self.handlers = {}

    def register(self, name, handler):
        self.handlers[name] = handler


class BridgeFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.path = root / "bean-reasoning.sqlite3"
        self.bridge_path = root / "bridge-evidence.sqlite3"
        self.model = ExperimentalModel()
        self.service = NativeReasoningService(self.path, model=self.model)
        self.addCleanup(self.service.close)
        self.runner = BridgeReasoningLoop(
            self.service, self.bridge_path, verifier=SourceVerifier())
        self.seed_measured_policy()

    def seed_measured_policy(self):
        self.service.reflect(
            domain="calibrate", task_id="observed-original",
            observed="FAIL", expected="PASS",
            adjustment_hypothesis="CALIBRATE use APPROVED_RULE for old instruments",
            evidence_refs=["fixture:old-development"])
        self.service.retain_skill(
            domain="calibrate", name="CALIBRATE alternative",
            steps=["CALIBRATE check instrument certificate"], passed=True,
            evidence_refs=["fixture:old-skill"])
        self.service.propose_instruction(
            domain="calibrate", instruction="CALIBRATE use old instructions",
            evidence_refs=["fixture:old-prompt"])
        self.service.reflect(
            domain="other", task_id="placebo",
            observed="wrong", expected="right",
            adjustment_hypothesis="unrelated geometry measurements",
            evidence_refs=["fixture:placebo"])
        dev = [
            TrialCase("cal-a", "calibrate", "CALIBRATE device A", "PASS"),
            TrialCase("cal-b", "calibrate", "CALIBRATE device B", "PASS"),
        ]
        selection = self.service.evaluate_and_select(
            domain="calibrate", cases=dev, model=self.model,
            judge=lambda expect, actual: expect == actual)
        self.assertEqual(selection["selection"]["arm"], "reflection")
        self.assertEqual(selection["trial"]["scores"], {
            "cold": 0, "reflection": 2, "skill": 0,
            "prompt": 0, "placebo": 0})

    @staticmethod
    def evidence(kind="two", suffix=""):
        good = lambda label, origin: {
            "ref": "fixture:trusted:" + label + suffix,
            "origin": origin, "value": "GREEN"}
        if kind == "one":
            return [good("lab-a", "lab-a")]
        if kind == "same-origin":
            return [good("lab-a", "lab-a"), good("lab-b", "lab-a")]
        if kind == "contradiction":
            return [good("lab-a", "lab-a"),
                    {"ref": "fixture:unknown:lab-b" + suffix,
                     "origin": "lab-b", "value": "BLUE"}]
        if kind == "unverified":
            return [
                {"ref": "fixture:unknown:lab-a" + suffix, "origin": "lab-a",
                 "value": "GREEN"},
                {"ref": "fixture:unknown:lab-b" + suffix, "origin": "lab-b",
                 "value": "GREEN"},
            ]
        return [good("lab-a", "lab-a"), good("lab-b", "lab-b")]

    def experiment(self, *, concept, observations, task_ref,
                   query=None):
        return self.runner.attempt(
            domain="calibrate", task_ref=task_ref, concept=concept,
            query=query or f"SENSOR CALIBRATE {concept} measurement",
            as_of="2026-10-25T14:00:00Z", observations=observations)

    def test_real_bridge_evidence_to_correction_then_frozen_new_task_improves(self):
        # First decision is wrong; its source must be captured before Bridge.
        before = self.experiment(
            concept="sensor_a", observations=self.evidence(),
            task_ref="before-learning")
        self.assertEqual(before["reasoning_answer"], "RED")
        self.assertTrue(before["feedback_applied"])
        self.assertFalse(before["matched"])
        self.assertTrue(before["correction_added"])
        self.assertEqual(before["bridge_status"], "committed_verified_revision")
        self.assertEqual(len(before["source_refs"]), 2)
        self.assertEqual(self.service.status()["feedback_receipts"], 1)
        self.assertIn("GREEN", self.service.recall(
            domain="calibrate", query="SENSOR CALIBRATE sensor_a",
            strategy="reflection")[0]["text"])

        # The same frozen model and unchanged selected strategy receive the
        # new BEAN-owned lesson. The model didn't see expected answers earlier.
        after = self.experiment(
            concept="sensor_a", observations=self.evidence("two", "-fresh"),
            task_ref="second-task",
            query="SENSOR CALIBRATE sensor_a followup-new-instance")
        self.assertEqual(after["reasoning_answer"], "GREEN")
        self.assertTrue(after["feedback_applied"])
        self.assertTrue(after["matched"])
        self.assertEqual(after["bridge_status"], "corroborated_no_revision")
        self.assertFalse(after["correction_added"])

        # Frozen holdout is distinct from development, never used to reselect.
        self.service.close()
        reopened = NativeReasoningService(self.path, model=self.model)
        try:
            holdout = reopened.evaluate_holdout(
                domain="calibrate",
                cases=[
                    TrialCase("hold-s1", "calibrate",
                              "SENSOR CALIBRATE sensor_a unseen lot 81", "GREEN"),
                    TrialCase("hold-s2", "calibrate",
                              "SENSOR CALIBRATE sensor_a unseen lot 82", "GREEN"),
                ],
                model=self.model, judge=lambda expected, actual: expected == actual)
            scores = holdout["trial"]["scores"]
            self.assertEqual(scores, {"cold": 0, "placebo": 0, "adaptive": 2})
            self.assertEqual(holdout["scope"], "post_selection_holdout_no_policy_change")
            self.assertEqual(reopened.status()["feedback_receipts"], 2)
            self.assertEqual(reopened.status()["selected_strategies"], 1)
            self.assertEqual(reopened.bank.selected_arm("calibrate"), "reflection")
            self.assertEqual(material_for(reopened.bank, "cold", "calibrate"),
                             "")
        finally:
            reopened.close()

    def test_case_specific_bridge_lessons_do_not_leak_into_other_sensors(self):
        self.experiment(
            concept="sensor_a", observations=self.evidence(),
            task_ref="learn-sensor-a")
        from bean.learning.experimental import material_for
        same = material_for(self.service.bank, "adaptive", "calibrate",
                            query="SENSOR CALIBRATE sensor_a new sample")
        other = material_for(self.service.bank, "adaptive", "calibrate",
                             query="SENSOR CALIBRATE sensor_b new sample")
        near = material_for(self.service.bank, "adaptive", "calibrate",
                            query="SENSOR CALIBRATE sensor_a1 new sample")
        self.assertIn("GREEN", same)
        self.assertNotIn("GREEN", other)
        self.assertNotIn("GREEN", near)

    def test_single_origin_conflict_and_unchecked_sources_never_create_lessons(self):
        for kind in ("one", "same-origin", "contradiction", "unverified"):
            run = self.experiment(
                concept="new-" + kind, observations=self.evidence(kind),
                task_ref=kind)
            self.assertFalse(run["feedback_applied"], kind)
            self.assertFalse(run["source_agreement"], kind)
            self.assertEqual(run["reasoning_answer"], "RED")
        self.assertEqual(self.service.status()["feedback_receipts"], 0)
        self.assertEqual(self.service.status()["selected_strategies"], 1)

    def test_bad_json_sources_fail_before_spending_model_request(self):
        old = len(self.model.calls)
        with self.assertRaises(TypeError):
            self.experiment(
                concept="invalid", task_ref="bad",
                observations=[{"ref": "fake", "origin": "fake",
                               "value": "GREEN", "verified": True}])
        self.assertEqual(len(self.model.calls), old)

    def test_inbox_uses_trusted_host_verifier_not_client_grade(self):
        inbox = SimpleInbox()
        register_bridge_feedback_handler(inbox, self.runner)
        self.assertIn("reasoning_bridge_experiment", inbox.handlers)
        import types
        msg = types.SimpleNamespace(args={
            "domain": "calibrate", "task_ref": "inbox-a",
            "query": "SENSOR CALIBRATE sensor_z new",
            "concept": "sensor_z", "as_of": "2026-10-25T14:00:00Z",
            "observations": self.evidence()})
        got = inbox.handlers["reasoning_bridge_experiment"](msg, "session")
        self.assertTrue(got["feedback_applied"])
        self.assertEqual(self.service.status()["feedback_receipts"], 1)


if __name__ == "__main__":
    unittest.main()

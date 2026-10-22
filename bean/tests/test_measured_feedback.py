"""Evaluate complete/incomplete rewards, durable restart and duplicate blocking."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bean.learning.runtime import LearningRuntime, register_learning_handlers
from bean.learning.measured_feedback import MeasuredFeedback

class Inbox:
    def __init__(self): self.handlers = {}
    def register(self, name, handler): self.handlers[name] = handler
    def call(self, name, **args):
        return self.handlers[name](SimpleNamespace(args=args), "test")

class MeasuredFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "learning.sqlite"
        self.service = LearningRuntime(self.path, actions=("left","right"), seed=7)
        self.addCleanup(self.service.close)
        self.bridge = MeasuredFeedback(self.service)

    def choose(self, episode_id="e1"):
        return self.service.choose(
            episode_id=episode_id, domain="reasoning_strategy",
            state={"task":"fixture-v1"}, location_ref="task1",
            legal_actions=["left","right"])

    @staticmethod
    def trial(**kw):
        result = dict(
            experiment="transfer", metric="cases_correct",
            condition_id="same-tasks", baseline_run="base",
            candidate_run="trained", baseline=10.0, candidate=20.0,
            direction="higher", matched_cases=40, expected_cases=40,
            evaluation_sha256="1"*64,
            evidence_ref="https://example.org/attested-measurements.json",
            evidence_kind="synthetic")
        result.update(kw)
        return result

    def test_reward_changes_real_q_and_survives_restart(self):
        chosen = self.choose()
        receipt = self.bridge.record(episode_id="e1",trial=self.trial())
        self.assertTrue(receipt["learned"])
        self.assertTrue(receipt["durable_checkpoint"])
        self.assertEqual(receipt["q_step"],1)
        key = self.service.policy.key(
            self.service.scoped("reasoning_strategy",{"task":"fixture-v1"}))
        self.assertGreater(
            self.service.policy.q[key][chosen["action_index"]],0)
        prior = self.service.policy.q
        self.assertEqual(len(self.bridge.history()["records"]),1)
        restored = LearningRuntime(self.path, actions=("left","right"),seed=7)
        self.addCleanup(restored.close)
        self.assertEqual(restored.policy.q, prior)
        self.assertEqual(restored.policy.steps,1)
        bridge = MeasuredFeedback(restored)
        self.assertEqual(len(bridge.history()["records"]),1)
        self.choose(episode_id="e2")
        dup = self.bridge.record(episode_id="e2",trial=self.trial())
        self.assertFalse(dup["new_reward"])
        self.assertEqual(self.service.policy.steps,1)

    def test_negative_reward_is_a_negative_q_update(self):
        chosen = self.choose()
        receipt = self.bridge.record(
            episode_id="e1",
            trial=self.trial(
                baseline=20.0,candidate=10.0,
                evaluation_sha256="2"*64))
        self.assertTrue(receipt["new_reward"])
        self.assertLess(receipt["reward"],0)
        key=self.service.policy.key(
            self.service.scoped("reasoning_strategy",{"task":"fixture-v1"}))
        self.assertLess(self.service.policy.q[key][chosen["action_index"]],0)

    def test_incomplete_or_same_run_is_not_credited(self):
        self.choose()
        for changed in (dict(matched_cases=39), dict(candidate_run="base"),
                        dict(matched_cases=20,expected_cases=20)):
            result=self.bridge.record(
                episode_id="e1",trial=self.trial(**changed))
            self.assertFalse(result["learned"])
        self.assertEqual(self.service.policy.steps,0)
        self.assertEqual(self.bridge.history()["records"],[])

    def test_direction_lower_and_tie(self):
        self.choose()
        response=self.bridge.record(episode_id="e1",trial=self.trial(
            metric="latency",baseline=50.,candidate=30.,
            direction="lower",evaluation_sha256="3"*64))
        self.assertGreater(response["reward"],0)
        self.choose(episode_id="e2")
        result=self.bridge.record(episode_id="e2",trial=self.trial(
            baseline=40.,candidate=40.,
            evaluation_sha256="4"*64))
        self.assertEqual(result["reward"],0)
        self.assertTrue(result["learned"])

    def test_duplicate_renamed_run_is_not_new_credit(self):
        self.choose()
        self.bridge.record(episode_id="e1",trial=self.trial())
        self.choose(episode_id="e2")
        with self.assertRaisesRegex(ValueError,"immutable receipt conflict"):
            self.bridge.record(episode_id="e2",trial=self.trial(
                candidate_run="renamed"))
        self.assertEqual(self.service.policy.steps,1)

    def test_failed_checkpoint_rolls_back_q_and_receipt(self):
        from unittest.mock import patch
        self.choose()
        with patch.object(self.service, "checkpoint",
                          side_effect=RuntimeError("checkpoint disk error")):
            with self.assertRaisesRegex(RuntimeError, "checkpoint disk error"):
                self.bridge.record(episode_id="e1",trial=self.trial(
                    evaluation_sha256="5"*64))
        self.assertEqual(self.service.policy.steps,0)
        self.assertEqual(self.bridge.history()["records"],[])
        # Choice is still pending after the failed assessment.
        valid=self.bridge.record(episode_id="e1",trial=self.trial(
            evaluation_sha256="6"*64))
        self.assertTrue(valid["durable_checkpoint"])

    def test_inbox_end_to_end(self):
        inbox=register_learning_handlers(Inbox(),self.service)
        decision=inbox.call(
            "learning_choose",episode_id="box",domain="strategy",
            state=[1],location_ref=[0],legal_actions=["left","right"])
        self.assertIn(decision["action"],("left","right"))
        r=inbox.call("learning_evaluated_feedback",episode_id="box",
                     trial=self.trial(evaluation_sha256="7"*64))
        self.assertTrue(r["durable_checkpoint"])
        self.assertEqual(len(inbox.call("learning_reward_history")["records"]),1)
        self.assertEqual(inbox.call("learning_status")["q_updates"],1)

if __name__=="__main__":
    unittest.main()

"""BEAN local selective-transfer regression and negative-transfer tests."""
import hashlib
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

from bean.learning.transfer_gate import evaluate_transfer
from bean.learning.reasoning_service import NativeReasoningService


def fixture_reward(policy, case, *, objective):
    """Simulated paired intervention, not a supplied reward label."""
    rng = random.Random(int(case))
    x = rng.uniform(-.75, .75)
    goal = rng.uniform(-.65, .65)
    earned = 0.0
    for _ in range(10):
        before = -abs(goal-x) if objective == "match" else x
        if policy == "retained":
            movement = 0.11 if goal > x else -0.11
        elif policy == "fresh":
            movement = 0.11
        else:
            raise ValueError("Unknown controller")
        x = min(1.0, max(-1.0, x + movement))
        after = -abs(goal-x) if objective == "match" else x
        earned += after-before-.003
    return earned


class SelectiveTransferTests(unittest.TestCase):
    def test_positive_task_favors_prior_on_paired_evidence(self):
        ids=[str(10000+i) for i in range(10)]
        decision=evaluate_transfer(
            retained="retained", alternative="fresh", probe_ids=ids,
            reward=lambda candidate, seed: fixture_reward(
                candidate, seed, objective="match"))
        self.assertTrue(decision["transfer_accepted"])
        self.assertEqual(decision["selected"], "retained")
        self.assertEqual(decision["comparison_result"], "reuse_retained")
        self.assertEqual(len(decision["pairs"]), len(ids))
        blinded=[str(30000+i) for i in range(100)]
        score_retained=sum(fixture_reward("retained", s, objective="match") for s in blinded)
        score_fresh=sum(fixture_reward("fresh", s, objective="match") for s in blinded)
        self.assertGreater(score_retained,score_fresh)

    def test_negative_task_rejects_harmful_transfer(self):
        ids=[str(20000+i) for i in range(10)]
        decision=evaluate_transfer(
            retained="retained", alternative="fresh", probe_ids=ids,
            reward=lambda candidate, seed: fixture_reward(
                candidate, seed, objective="different"))
        self.assertFalse(decision["transfer_accepted"])
        self.assertEqual(decision["selected"], "fresh")
        self.assertEqual(decision["comparison_result"], "prefer_alternative")
        blinded=[str(40000+i) for i in range(100)]
        a=sum(fixture_reward("retained", s, objective="different") for s in blinded)
        b=sum(fixture_reward("fresh", s, objective="different") for s in blinded)
        self.assertGreater(b,a)

    def test_inconclusive_rewards_abstain(self):
        response=evaluate_transfer(retained="a", alternative="b",
            probe_ids=["calibration-only"],
            reward=lambda policy, case: 1.0)
        self.assertFalse(response["transfer_accepted"])
        self.assertEqual(response["decision"], "reject_or_abstain")
        self.assertIsNone(response["selected"])
        self.assertEqual(response["comparison_result"], "inconclusive_abstain")
        self.assertEqual(response["average_advantage"], 0.0)
        self.assertEqual(len(response["pairs"]), 1)

    def test_insufficient_margin_abstains_without_promoting_either_policy(self):
        for preferred in ("retained", "alternative"):
            with self.subTest(preferred=preferred):
                def reward(policy, case):
                    return 1.0 if policy == preferred else 0.0
                response = evaluate_transfer(
                    retained="retained", alternative="alternative",
                    probe_ids=["trial-1", "trial-2"], reward=reward,
                    margin=1.0)
                self.assertIsNone(response["selected"])
                self.assertFalse(response["transfer_accepted"])
                self.assertEqual(response["comparison_result"],
                                 "inconclusive_abstain")
                self.assertEqual(response["required_margin"], 1.0)

    def test_core_persists_abstention_and_recovers_original_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "abstain.sqlite3"
            brain = NativeReasoningService(db)
            decision = brain.test_analogy(
                domain="controls", task_ref="inconclusive-transfer",
                source_ref="fixture:equal-feedback",
                retained="retained", alternative="fresh",
                probe_ids=["heldout-excluded-1", "heldout-excluded-2"],
                reward=lambda *_: 0.5)
            self.assertIsNone(decision["selected"])
            self.assertEqual(decision["comparison_result"],
                             "inconclusive_abstain")
            brain.close()
            reopened = NativeReasoningService(db)
            try:
                trials = [e["data"] for e in reopened.bank.journal.events()
                          if e["kind"] == "trial" and e["data"].get(
                              "experiment") == "bean.native.selective_transfer.v1"]
                self.assertEqual(len(trials), 1)
                self.assertIsNone(trials[0]["decision"]["selected"])
                self.assertEqual(trials[0]["decision"]["evidence_sha256"],
                                 decision["evidence_sha256"])
            finally:
                reopened.close()

    def test_invalid_evidence_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_transfer(retained="a", alternative="b",
                probe_ids=["repeat","repeat"],reward=lambda *_: 0.)
        with self.assertRaises(ValueError):
            evaluate_transfer(retained="a", alternative="b",
                probe_ids=["1"],reward=lambda *_: float("nan"))
        with self.assertRaises(ValueError):
            evaluate_transfer(retained="a", alternative="b",
                probe_ids=["1"],reward=lambda *_: 0.,margin=-1)
        with self.assertRaises(ValueError):
            evaluate_transfer(retained="same", alternative="same",
                probe_ids=["1"],reward=lambda *_: 0.)

    def test_core_persists_decision_and_reopens_without_provider(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"bean.sqlite3"
            brain=NativeReasoningService(db)
            outcome=brain.test_analogy(
                domain="manufacturing", task_ref="sensor-task-1",
                source_ref="source:independent-breakout-neural-checkpoint",
                retained="retained", alternative="fresh",
                probe_ids=[str(22000+i) for i in range(3)],
                reward=lambda candidate, seed: fixture_reward(
                    candidate,seed,objective="different"))
            self.assertFalse(outcome["model_invoked"])
            brain.close()
            reopened=NativeReasoningService(db)
            try:
                events=[e for e in reopened.bank.journal.events()
                        if e["kind"]=="trial" and
                        e["data"].get("experiment")=="bean.native.selective_transfer.v1"]
                self.assertEqual(len(events),1)
                self.assertEqual(events[0]["data"]["decision"]["evidence_sha256"],
                    outcome["evidence_sha256"])
                self.assertEqual(events[0]["data"]["decision"]["selected"],"fresh")
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()

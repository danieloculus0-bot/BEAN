"""Prove actual feedback, Q values, restart recovery, and inbox wiring."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bean.learning.runtime import LearningRuntime, register_learning_handlers


class FakeInbox:
    def __init__(self):
        self.handlers = {}

    def register(self, name, handler):
        self.handlers[name] = handler

    def call(self, name, **args):
        return self.handlers[name](SimpleNamespace(args=args), "test-session")


class LearningRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "learn.sqlite"
        self.service = LearningRuntime(self.db, actions=("left", "right"), seed=2)
        self.addCleanup(self.service.close)

    def choice(self, episode_id="ep1", domain="maze"):
        return self.service.choose(
            episode_id=episode_id, domain=domain, state={"x": 0},
            location_ref="node-A", legal_actions=["left", "right"],
            candidate_destinations={"left": "node-B", "right": "node-C"})

    def test_real_reward_updates_q_without_fake_automatic_training(self):
        result = self.choice()
        self.assertIn(result["action"], ("left", "right"))
        self.assertFalse(result["learned_this_decision"])
        self.assertEqual(self.service.status()["q_updates"], 0)
        with self.assertRaisesRegex(ValueError, "feedback required"):
            self.choice()
        receipt = self.service.feedback(
            episode_id="ep1", reward=5.0, done=True)
        self.assertTrue(receipt["learned"])
        self.assertEqual(self.service.status()["q_updates"], 1)
        self.assertEqual(self.service.status()["active_episodes"], 0)
        key = self.service.policy.key(self.service.scoped("maze", {"x": 0}))
        self.assertGreater(max(self.service.policy.q[key]), 0)
        with self.assertRaisesRegex(ValueError, "no uncredited choice"):
            self.service.feedback(episode_id="ep1", reward=5.0, done=True)

    def test_checkpoint_and_restart_recover_identical_q(self):
        self.choice()
        self.service.feedback(episode_id="ep1", reward=2.0, done=True)
        original = dict(self.service.policy.q)
        receipt = self.service.checkpoint(
            baseline=0, candidate=10, samples=40,
            evaluation_sha256="a" * 64)
        self.assertTrue(receipt["checkpoint_saved"])
        self.assertEqual(self.service.status()["checkpoints"], 1)
        reopened = LearningRuntime(self.db, actions=("left", "right"), seed=2)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.policy.q, original)
        self.assertEqual(reopened.status()["q_updates"], 1)
        self.assertEqual(reopened.status()["checkpoints"], 1)

    def test_reject_misleading_feedback_and_mixed_domains(self):
        with self.assertRaises(ValueError):
            self.service.feedback(episode_id="ep1", reward=2, done=True)
        with self.assertRaises(ValueError):
            self.service.choose(
                episode_id="ep1", domain="maze", state=1,
                location_ref=2, legal_actions=["unknown"])
        self.choice()
        with self.assertRaises(ValueError):
            self.choice(domain="trades")
        with self.assertRaises(ValueError):
            self.service.feedback(
                episode_id="ep1", reward=float("nan"), done=True)
        self.assertEqual(self.service.status()["q_updates"], 0)
        self.service.feedback(episode_id="ep1", reward=-1, done=True)

    def test_domain_specific_states_do_not_share_q_values(self):
        self.choice(episode_id="a", domain="maze")
        self.service.feedback(episode_id="a", reward=4, done=True)
        maze_key = self.service.policy.key(self.service.scoped("maze", {"x": 0}))
        trade_key = self.service.policy.key(self.service.scoped("trades", {"x": 0}))
        self.assertIn(maze_key, self.service.policy.q)
        self.assertNotIn(trade_key, self.service.policy.q)

    def test_inbox_wires_real_learning_operations(self):
        inbox = register_learning_handlers(FakeInbox(), self.service)
        decision = inbox.call(
            "learning_choose", episode_id="box", domain="maze",
            state=[0], location_ref=[0, 0],
            legal_actions=["left", "right"])
        self.assertIn(decision["action"], ("left", "right"))
        result = inbox.call(
            "learning_feedback", episode_id="box", reward=3, done=True)
        self.assertEqual(result["q_updates"], 1)
        self.assertEqual(inbox.call("learning_status")["q_updates"], 1)
        receipt = inbox.call(
            "learning_checkpoint", baseline=1, candidate=2, samples=30,
            evaluation_sha256="b" * 64)
        self.assertTrue(receipt["checkpoint_saved"])


if __name__ == "__main__":
    unittest.main()

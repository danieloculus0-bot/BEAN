"""Regression tests for a reachable Breakout win and neural demonstration."""
import tempfile
import unittest
from pathlib import Path

import torch

from bean.optimization.sponge_dqn import SpongeDQN
from experiments.breakout_learning.game import Breakout
from experiments.breakout_learning.marathon import (
    demonstrate, teaching_action, load_resume, run, TARGET_BRICKS,
)


def simple_tracker(state):
    return teaching_action(state)


class BreakoutWinMarathonTests(unittest.TestCase):
    def test_original_score_window_is_untouched(self):
        e = Breakout(1)
        result = e.play(simple_tracker)
        self.assertEqual(result["frames"], 1000)
        self.assertLess(result["bricks"], TARGET_BRICKS)
        self.assertFalse(result["won"])

    def test_24_brick_clearance_is_reachable(self):
        e = Breakout(1, max_steps=5000)
        result = e.play(simple_tracker)
        self.assertEqual(result["bricks"], TARGET_BRICKS)
        self.assertEqual(result["won"], 1)
        self.assertLess(result["frames"], 5000)

    def test_neural_weights_really_learn_teacher_and_win_without_teacher(self):
        torch.set_num_threads(1)
        agent = SpongeDQN(seed=20261025, domain="breakout-marathon",
                          batch_size=32, replay_capacity=12000,
                          warmup=256, learn_every=4, target_sync=300,
                          lr=.0007, gamma=.99)
        before = agent.weights_digest()
        teaching = demonstrate(agent, updates=250)
        self.assertGreaterEqual(teaching["demonstration_fidelity"], 0.98)
        self.assertNotEqual(agent.weights_digest(), before)
        replay = Breakout(1, max_steps=5000).play(
            lambda state: agent.choose(state, epsilon=0.0))
        self.assertEqual(replay["won"], 1)

    def test_real_training_cycle_journal_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run(Path(directory), episode_budget=1)
            self.assertEqual(result["status"], "won")
            self.assertTrue(result["checkpoint_recovery_verified"])
            self.assertTrue(result["real_win_on_unseen_seed"])
            saved = load_resume(Path(directory))
            self.assertEqual(saved[1]["cycle"], 1)
            self.assertEqual(saved[1]["episode"], 1)


if __name__ == "__main__":
    unittest.main()

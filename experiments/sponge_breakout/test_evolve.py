"""Neuroevolution must inherit, mutate, learn by gradient and preserve evidence."""
import math
import tempfile
import unittest
from pathlib import Path

import torch

from bean.optimization.sponge_dqn import SpongeDQN
from bean.optimization.autodev import Journal
from bean.memory.compression import recover_memory
from .evolve import breed, compete, OBJECTIVE, fingerprint


class NeuralEvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_backprop_updates_real_neural_weights(self):
        learner = SpongeDQN(seed=7, batch_size=4, warmup=4,
                            replay_capacity=20, learn_every=1, target_sync=2)
        before = [p.detach().clone() for p in learner.online.parameters()]
        for frame in range(24):
            loss = learner.observe((5, 0, 1), frame % 3, 2.0,
                                   (9, 1, 0), False)
        self.assertTrue(math.isfinite(loss))
        self.assertGreater(learner.updates, 2)
        self.assertTrue(any(not torch.equal(a,b) for a,b in zip(before,learner.online.parameters())))
        self.assertEqual(len(learner.replay),20)

    def test_offspring_inherit_mutate_and_reproduce_seed(self):
        config = {"lr": .0007, "gamma": .99, "epsilon_floor": .06}
        parent, _ = breed(None, config, seed=123, mutate=False)
        parent_weights = parent.weights()
        cloned, inherited = breed(parent_weights, config, seed=55, mutate=False)
        self.assertEqual(cloned.weights(), parent_weights)
        self.assertEqual(inherited, config)
        a, ac = breed(parent_weights, config, seed=55, mutate=True)
        b, bc = breed(parent_weights, config, seed=55, mutate=True)
        self.assertEqual(a.weights(),b.weights())
        self.assertEqual(ac,bc)
        self.assertNotEqual(a.weights(),parent_weights)
        self.assertNotEqual(fingerprint(a.weights()), fingerprint(parent_weights))
        self.assertEqual(a.choose((6,1,0),epsilon=0), b.choose((6,1,0),epsilon=0))

    def test_small_generation_evidence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = compete(Path(tmp)/"trial", seed=1, population=2, generations=2,
                             games_per_candidate=2, validation_games=30, holdout_games=30)
            self.assertEqual(len(report["lineage"]),4)
            self.assertEqual(len(report["champions"]),2)
            self.assertIn("gain_over_single_dqn",report)
            self.assertEqual(report["protocol"]["control_game_budget"],8)
            self.assertEqual(report["holdout"]["evolved_dqn"]["games"],30)
            journal = Journal(Path(tmp)/"trial"/"evolution.sqlite")
            events = journal.events(OBJECTIVE)
            self.assertEqual(len(events),4)
            self.assertTrue(all(event["quality"]["verification"] ==
                                "host_attested_not_independently_verified" for event in events))
            self.assertTrue(all(fingerprint(recover_memory(event["memory"])) ==
                                event["memory"]["sha256"] for event in events))
            journal.close()

if __name__ == "__main__":
    unittest.main()

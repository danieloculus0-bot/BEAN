"""Neuroevolution must inherit, mutate, learn by gradient and preserve evidence."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import torch

from bean.optimization.sponge_dqn import SpongeDQN
from bean.optimization.autodev import Journal
from bean.memory.compression import recover_memory
from .evolve import breed, compete, OBJECTIVE, fingerprint, promotion_gate


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

    def test_lineage_preserves_replay_optimizer_and_learning_clock(self):
        config = {"lr": .0007, "gamma": .99, "epsilon_floor": .06}
        parent, _ = breed(None, config, seed=17, mutate=False)
        for i in range(300):
            parent.observe((5, 0, 1), i % 3, 1.0, (6, 1, 0), False)
        state = parent.learner_state()
        child, _ = breed(state, config, seed=18, mutate=False)
        self.assertEqual(child.frames, parent.frames)
        self.assertEqual(child.updates, parent.updates)
        self.assertEqual(len(child.replay), len(parent.replay))
        self.assertEqual(child.weights(), parent.weights())
        self.assertEqual(child.optimizer.state_dict()["state"].keys(),
                         parent.optimizer.state_dict()["state"].keys())
        self.assertEqual(child.rng.getstate(), parent.rng.getstate())
        mutated, _ = breed(state, config, seed=19, mutate=True)
        self.assertEqual(mutated.frames, parent.frames)
        self.assertNotEqual(mutated.weights(), parent.weights())

    def test_continuation_preserves_budget_and_final_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "trial"
            result = compete(folder, seed=4, population=2, generations=2,
                             games_per_candidate=2, continuation_games=5,
                             validation_games=30, holdout_games=30)
            self.assertEqual(result["protocol"]["search_game_budget"], 8)
            self.assertEqual(result["protocol"]["continuation_games"], 5)
            self.assertEqual(result["protocol"]["control_game_budget"], 13)
            final_weights = json.loads(
                (folder / "final-evolved-weights.json").read_text(encoding="utf-8"))
            self.assertEqual(fingerprint(final_weights), result["final_policy_sha256"])
            self.assertGreater(result["selected_training"]["frames"], 0)
            self.assertGreater(result["control_training"]["frames"], 0)
            self.assertEqual(result["holdout"]["adopted_policy"],
                             result["holdout"][result["promotion_gate"]["decision"]])

    def test_terminal_safe_potential_preserves_discounted_episode_objective(self):
        from .evolve import paddle_potential, shape_training_reward
        gamma = .99
        first, middle = (14, 1, 1), (10, 1, 1)
        self.assertEqual(paddle_potential((14, 1, 0)), 0.0)
        self.assertEqual(paddle_potential(None), 0.0)
        raw = 0.8 + gamma * -2.0
        shaped = (shape_training_reward(.8, first, middle, gamma)
                  + gamma * shape_training_reward(-2.0, middle, None, gamma))
        self.assertAlmostEqual(shaped, raw - paddle_potential(first), places=10)
        self.assertAlmostEqual(shape_training_reward(.8, (7, 0, 0), None, gamma),
                               .8)

    def test_unshaped_control_observes_raw_environment_reward(self):
        from .evolve import train_game
        from .game import Breakout

        class Spy:
            gamma = .99
            frames = 0
            def __init__(self):
                self.rewards = []
            def choose(self, _state, epsilon=0.0):
                return 1
            def observe(self, _before, _action, reward, _after, _done):
                self.rewards.append(reward)
                self.frames += 1

        control = Spy()
        evolved = Spy()
        train_game(control, 900053, .06)
        train_game(evolved, 900053, .06, shaped=True)
        raw_game = Breakout(900053)
        raw = []
        while not raw_game.done:
            raw.append(raw_game.step(1))
        self.assertEqual(control.rewards, raw)
        self.assertEqual(len(evolved.rewards), len(raw))
        self.assertNotEqual(evolved.rewards, raw)
        self.assertEqual(control.frames, evolved.frames)

    def test_adoption_gate_requires_both_validation_cohorts(self):
        def metrics(bricks, survival, first):
            return {"bricks": bricks, "survival": survival, "games": 60, "seed_start": first}
        control = [metrics(8, .8, 100), metrics(9, .9, 200)]
        clear = [metrics(8.7, .8, 100), metrics(9.3, .91, 200)]
        self.assertTrue(promotion_gate(clear, control)["accepted"])
        overfit = [metrics(12, .95, 100), metrics(8, .4, 200)]
        rejection = promotion_gate(overfit, control)
        self.assertFalse(rejection["accepted"])
        self.assertFalse(rejection["cohorts"][1]["accepted"])
        self.assertFalse(promotion_gate(
            [metrics(9, .2, 100), metrics(10, .92, 200)], control)["accepted"])
        with self.assertRaises(ValueError):
            promotion_gate(clear, control[:1])

    def test_small_generation_evidence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = compete(Path(tmp)/"trial", seed=1, population=2, generations=2,
                             games_per_candidate=2, validation_games=30, holdout_games=30)
            self.assertEqual(len(report["lineage"]),4)
            self.assertEqual(len(report["champions"]),2)
            self.assertIn("gain_over_single_dqn",report)
            self.assertEqual(report["protocol"]["validation_cohorts"], 2)
            self.assertIn(report["promotion_gate"]["decision"], ("dqn_no_evolution", "evolved_dqn"))
            self.assertEqual(report["holdout"]["adopted_policy"],
                             report["holdout"][report["promotion_gate"]["decision"]])
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

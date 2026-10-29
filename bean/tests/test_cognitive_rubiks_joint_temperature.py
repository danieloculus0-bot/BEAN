"""Targeted BEAN-native joint-temperature learning and receipt regression tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet import rubiks3
from experiments.cognitive_gauntlet.rubiks3_joint_temperature import (
    pair_distances, joint_temperature_reward, train_joint_temperature,
    experiment, verify_receipt,
)
from experiments.cognitive_gauntlet.rubiks3_pair_goals import (
    pair_features, train_pairs,
)
from experiments.cognitive_gauntlet.rubiks3_pieces import observed_edges
from experiments.cognitive_gauntlet.rubiks3_sponge import _digest, collect_states
from experiments.cognitive_gauntlet.rubiks3_joint_rescue import (
    policy_solve_joint_rescue,
)
from experiments.cognitive_gauntlet.rubiks3_symmetry import learn_symmetric


class JointTemperatureTests(unittest.TestCase):
    def test_pair_features_and_legal_distances_align(self):
        for state in (rubiks3.SOLVED,
                      rubiks3.apply(rubiks3.SOLVED, ("R", "U", "F")),
                      rubiks3.apply(rubiks3.SOLVED, rubiks3.scramble(1251, 20))):
            measured = pair_distances(state)
            old = pair_features(state)
            self.assertEqual(len(measured), 96)
            self.assertEqual(tuple((pid, config, solved)
                                   for pid, config, _, solved in measured), old)
            self.assertTrue(all(all(type(d) is int and d >= 0 for d in distances)
                                for _, _, distances, _ in measured))

    def test_hotter_colder_and_no_repeated_completion_reward(self):
        gamma = .9
        hotter = joint_temperature_reward((2, 1), (1, 1),
                                           (False, False), (False, False), gamma)
        unchanged = joint_temperature_reward((2, 1), (2, 1),
                                              (False, False), (False, False), gamma)
        colder = joint_temperature_reward((2, 1), (3, 1),
                                           (False, False), (False, False), gamma)
        self.assertGreater(hotter, unchanged)
        self.assertGreater(unchanged, colder)
        self.assertGreater(joint_temperature_reward(
            (1, 0), (0, 0), (False, True), (True, True), gamma), 0)
        self.assertLessEqual(joint_temperature_reward(
            (0, 0), (0, 0), (True, True), (True, True), gamma), 0)
        with self.assertRaises(ValueError):
            joint_temperature_reward((-1, 0), (0, 0),
                                     (False, True), (True, True), gamma)

    def test_matched_updates_and_inference_has_no_teacher(self):
        states, _ = collect_states(range(3), (2, 3, 4))
        edges = observed_edges(states)
        with TemporaryDirectory() as tmp:
            full = SpongeTD(Path(tmp) / "full.db", actions=rubiks3.MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
            baseline = SpongeTD(Path(tmp) / "base.db", actions=rubiks3.MOVES,
                                alpha=1, gamma=.9, epsilon=0, seed=19)
            candidate = SpongeTD(Path(tmp) / "new.db", actions=rubiks3.MOVES,
                                 alpha=1, gamma=.9, epsilon=0, seed=19)
            try:
                learn_symmetric(full, states, epochs=1)
                train_pairs(baseline, edges, epochs=1)
                train_joint_temperature(candidate, edges, epochs=1)
                self.assertEqual(baseline.steps, candidate.steps)
                self.assertNotEqual(_digest(baseline.q), _digest(candidate.q))
                state = rubiks3.apply(rubiks3.SOLVED, ("R", "U", "F"))
                frozen = (_digest(full.q), _digest(candidate.q))
                with (patch.object(rubiks3, "solve",
                                   side_effect=AssertionError("solver leaked")),
                      patch.object(rubiks3, "scramble",
                                   side_effect=AssertionError("recipe leaked"))):
                    route, info = policy_solve_joint_rescue(
                        full, candidate, state, rescue_backup=True, work_budget=4)
                self.assertEqual(info["solved"],
                                 rubiks3.apply(state, route) == rubiks3.SOLVED)
                self.assertEqual(frozen, (_digest(full.q), _digest(candidate.q)))
            finally:
                full.close()
                baseline.close()
                candidate.close()

    def test_disjoint_holdout_receipt_and_independent_replay(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            record = experiment(train_seeds=range(3),
                                test_seeds=range(35000, 35002),
                                train_lengths=(2, 3), test_lengths=(3, 20),
                                epochs=1, work_budget=4, output=path)
            self.assertEqual(record["eligible_cases"] + record["excluded_count"], 4)
            self.assertEqual(record["baseline_training"]["td_updates"],
                             record["candidate_training"]["td_updates"])
            self.assertEqual(record["eligible_cases"], len(record["cases"]))
            self.assertTrue(verify_receipt(path)["verified"])
            for row in record["cases"]:
                self.assertEqual(row["candidate_solved"],
                                 rubiks3.apply(row["state"],
                                               row["candidate_moves"]) == rubiks3.SOLVED)
                self.assertFalse(row["optimality_proven"])
                self.assertEqual(row["candidate_paused"],
                                 row["candidate_checkpoint"] is not None)

    def test_forged_success_rejected_even_with_recomputed_checksum(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            experiment(train_seeds=range(2), test_seeds=[35100],
                       train_lengths=(2, 3), test_lengths=(20,),
                       epochs=1, work_budget=2, output=path)
            original = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(original["cases"])
            original["cases"][0]["candidate_solved"] = not original["cases"][0]["candidate_solved"]
            original["sha256"] = _digest(
                {k: v for k, v in original.items() if k != "sha256"})
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_receipt(path)


if __name__ == "__main__":
    unittest.main()

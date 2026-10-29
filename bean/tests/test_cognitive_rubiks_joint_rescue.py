"""Regression and independent replay for BEAN-native joint-cubie rescue."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet import rubiks3
from experiments.cognitive_gauntlet.rubiks3_joint_rescue import (
    experiment, policy_solve_joint_rescue,
)
from experiments.cognitive_gauntlet.rubiks3_joint_rescue_verify import verify_receipt
from experiments.cognitive_gauntlet.rubiks3_sponge import _digest
import json
from experiments.cognitive_gauntlet.rubiks3_pair_goals import (
    pair_features, train_pairs,
)
from experiments.cognitive_gauntlet.rubiks3_pieces import observed_edges
from experiments.cognitive_gauntlet.rubiks3_sponge import collect_states
from experiments.cognitive_gauntlet.rubiks3_symmetry import learn_symmetric
from experiments.cognitive_gauntlet.rubiks3_value_rollout import policy_solve_value_rollout


class JointRescueTests(unittest.TestCase):
    def test_successful_original_policy_is_unchanged_and_no_teacher_at_inference(self):
        states, _ = collect_states(range(4), (2, 3, 4))
        with TemporaryDirectory() as tmp:
            full = SpongeTD(Path(tmp) / 'full.db', actions=rubiks3.MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
            joint = SpongeTD(Path(tmp) / 'joint.db', actions=rubiks3.MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
            try:
                learn_symmetric(full, states, epochs=2)
                train_pairs(joint, observed_edges(states), epochs=1)
                state = rubiks3.turn(rubiks3.SOLVED, 'R')
                expected, info = policy_solve_value_rollout(full, state)
                self.assertTrue(info['solved'])
                frozen = (_digest(full.q), _digest(joint.q))
                with (patch.object(rubiks3, 'solve',
                                   side_effect=AssertionError('reference solver leaked')),
                      patch.object(rubiks3, 'scramble',
                                   side_effect=AssertionError('scramble leaked'))):
                    actual, result = policy_solve_joint_rescue(full, joint, state)
                self.assertEqual(actual, expected)
                self.assertTrue(result['solved'])
                self.assertEqual(result['joint_steps'], 0)
                self.assertEqual(frozen, (_digest(full.q), _digest(joint.q)))
            finally:
                full.close()
                joint.close()

    def test_checkpoint_resumes_and_rejects_changed_policy(self):
        state = rubiks3.turn(rubiks3.SOLVED, 'R')
        with TemporaryDirectory() as tmp:
            full = SpongeTD(Path(tmp) / 'full.db', actions=rubiks3.MOVES)
            joint = SpongeTD(Path(tmp) / 'joint.db', actions=rubiks3.MOVES)
            try:
                for pair_id, config, _ in pair_features(state):
                    joint.values((pair_id, config))[0] = .1
                route, info = policy_solve_joint_rescue(full, joint, state, work_budget=1)
                self.assertEqual(len(route), 1)
                self.assertTrue(info['paused'] or info['solved'])
                if info['paused']:
                    resumed, after = policy_solve_joint_rescue(
                        full, joint, state, checkpoint=info['checkpoint'],
                        work_budget=1)
                    self.assertGreaterEqual(len(resumed), len(route))
                    self.assertEqual(after['solved'],
                                     rubiks3.apply(state, resumed) == rubiks3.SOLVED)
                    with self.assertRaises(ValueError):
                        policy_solve_joint_rescue(
                            full, joint, rubiks3.SOLVED, checkpoint=info['checkpoint'])
                    joint.values((('corner', 'BAD'), (0,)))[0] = 0.3
                    with self.assertRaises(ValueError):
                        policy_solve_joint_rescue(
                            full, joint, state, checkpoint=info['checkpoint'])
            finally:
                full.close()
                joint.close()

    def test_heldout_receipts_and_matched_td_budget(self):
        result = experiment(train_seeds=range(3), test_seeds=range(28000, 28002),
                            train_lengths=(2, 3), test_lengths=(3, 20),
                            epochs=1, work_budget=8)
        self.assertEqual(result['eligible_cases'] + result['excluded_count'], 4)
        self.assertEqual(result['candidate_total_td_updates'],
                         result['matched_td_updates'])
        self.assertEqual(result['candidate_worse_than_initial'], 0)
        self.assertEqual(result['eligible_cases'], len(result['cases']))
        for row in result['cases']:
            self.assertEqual(row['candidate_solved'],
                             rubiks3.apply(row['state'], row['candidate_moves']) == rubiks3.SOLVED)
            self.assertEqual(row['candidate_move_count'], len(row['candidate_moves']))
            self.assertEqual(row['candidate_full_steps'] + row['candidate_joint_steps'],
                             row['candidate_move_count'])
            self.assertFalse(row['optimality_proven'])
            if row['candidate_paused']:
                self.assertEqual(row['candidate_checkpoint']['route'],
                                 row['candidate_moves'])

    def test_independent_receipt_replay_rejects_tampered_success(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'receipt.json'
            original = experiment(train_seeds=range(2), test_seeds=range(28100, 28101),
                                  train_lengths=(2, 3), test_lengths=(3, 20),
                                  epochs=1, work_budget=2, output=path)
            verified = verify_receipt(path)
            self.assertEqual(verified['candidate_solved'], original['candidate_solved'])
            tampered = json.loads(path.read_text(encoding='utf-8'))
            tampered['cases'][0]['candidate_solved'] = not tampered['cases'][0]['candidate_solved']
            tampered['sha256'] = _digest({k: v for k, v in tampered.items()
                                          if k != 'sha256'})
            path.write_text(json.dumps(tampered), encoding='utf-8')
            with self.assertRaises(ValueError):
                verify_receipt(path)

    def test_invalid_inputs_and_overlapping_seeds(self):
        with TemporaryDirectory() as tmp:
            full = SpongeTD(Path(tmp) / 'full.db', actions=rubiks3.MOVES)
            joint = SpongeTD(Path(tmp) / 'joint.db', actions=rubiks3.MOVES)
            try:
                with self.assertRaises(ValueError):
                    policy_solve_joint_rescue(full, joint, 'X' * 54)
                with self.assertRaises(ValueError):
                    policy_solve_joint_rescue(full, joint, rubiks3.SOLVED,
                                              work_budget=0)
            finally:
                full.close()
                joint.close()
        with self.assertRaises(ValueError):
            experiment(train_seeds=[1], test_seeds=[1])


if __name__ == '__main__':
    unittest.main()

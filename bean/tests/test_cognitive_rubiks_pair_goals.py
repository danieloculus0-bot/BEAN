"""Regression and independent-replay checks for BEAN's joint-cubie learner."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet import rubiks3
from experiments.cognitive_gauntlet.rubiks3_pair_goals import (
    experiment, joint_reward, pair_features, policy_solve_pairs, train_pairs,
)
from experiments.cognitive_gauntlet.rubiks3_pieces import observed_edges
from experiments.cognitive_gauntlet.rubiks3_sponge import _digest, collect_states


class JointGoalTests(unittest.TestCase):
    def test_joint_goal_not_single_piece_reward(self):
        self.assertEqual(joint_reward((False, False), (True, True)), 1.0)
        self.assertEqual(joint_reward((True, False), (True, True)), 1.0)
        self.assertEqual(joint_reward((True, True), (True, True)), 0.0)
        self.assertEqual(joint_reward((True, False), (True, False)), 0.0)
        self.assertEqual(joint_reward((False, False), (False, True)), 0.0)
        self.assertEqual(joint_reward((True, True), (False, True)), 0.0)

    def test_joint_features_have_stable_identity_and_legal_configs(self):
        home = pair_features(rubiks3.SOLVED)
        self.assertEqual(len(home), 96)
        self.assertEqual(len({p[0] for p in home}), 96)
        self.assertTrue(all(solved == (True, True) for _, _, solved in home))
        ids = tuple(p[0] for p in home)
        for move in rubiks3.MOVES:
            with self.subTest(move=move):
                after = pair_features(rubiks3.turn(rubiks3.SOLVED, move))
                self.assertEqual(ids, tuple(p[0] for p in after))
                self.assertTrue(any(solved != (True, True) for _, _, solved in after))

    def test_learned_joint_q_and_teacher_isolation_at_inference(self):
        states, _ = collect_states(range(5), (2, 3, 4))
        edges = observed_edges(states)
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'pairs.db', actions=rubiks3.MOVES,
                               alpha=1, gamma=.9, epsilon=0, seed=19)
            try:
                training = train_pairs(learner, edges, epochs=2)
                self.assertEqual(training['td_updates'], 2 * 96 * len(edges))
                self.assertGreater(len(learner.q), 0)
                frozen = _digest(learner.q)
                state = rubiks3.apply(rubiks3.SOLVED, rubiks3.scramble(25000, 20))
                with (patch.object(rubiks3, 'solve',
                                   side_effect=AssertionError('solver leaked')),
                      patch.object(rubiks3, 'scramble',
                                   side_effect=AssertionError('scramble leaked'))):
                    moves, info = policy_solve_pairs(learner, state)
                self.assertEqual(info['solved'],
                                 rubiks3.apply(state, moves) == rubiks3.SOLVED)
                self.assertEqual(frozen, _digest(learner.q))
            finally:
                learner.close()

    def test_compute_slice_checkpoint_resumes_without_move_limit(self):
        state = rubiks3.turn(rubiks3.SOLVED, 'R')
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'pairs.db', actions=rubiks3.MOVES,
                               alpha=1, gamma=.9, epsilon=0, seed=19)
            try:
                # Synthetic positive learned values are for checkpoint
                # mechanics only, not evidence of a trained solving policy.
                for pair_id, config, _ in pair_features(state):
                    learner.values((pair_id, config))[0] = 0.1
                first, info = policy_solve_pairs(learner, state, work_budget=1)
                self.assertEqual(len(first), 1)
                self.assertTrue(info['paused'] or info['solved'])
                if info['paused']:
                    with self.assertRaises(ValueError):
                        policy_solve_pairs(learner, rubiks3.SOLVED,
                                           checkpoint=info['checkpoint'])
                    resumed, after = policy_solve_pairs(
                        learner, state, checkpoint=info['checkpoint'],
                        work_budget=1)
                    self.assertGreaterEqual(len(resumed), len(first))
                    self.assertEqual(after['solved'],
                                     rubiks3.apply(state, resumed) == rubiks3.SOLVED)
            finally:
                learner.close()

    def test_reject_illegal_states(self):
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'pairs.db', actions=rubiks3.MOVES)
            try:
                with self.assertRaises(ValueError):
                    policy_solve_pairs(learner, 'X' * 54)
                with self.assertRaises(ValueError):
                    pair_features('X' * 54)
            finally:
                learner.close()

    def test_disjoint_holdout_matched_updates_and_every_case_replays(self):
        result = experiment(train_seeds=range(5), test_seeds=range(25000, 25003),
                            train_lengths=(2, 3, 4), test_lengths=(3, 20), epochs=1)
        self.assertEqual(result['eligible_cases'] + result['excluded_count'], 6)
        self.assertEqual(result['td_updates_per_arm'],
                         result['joint_training']['td_updates'])
        self.assertEqual(result['eligible_cases'], len(result['cases']))
        self.assertEqual(result['excluded_count'], len(result['excluded']))
        for row in result['cases']:
            self.assertEqual(row['baseline_solved'],
                             rubiks3.apply(row['state'], row['baseline_moves']) == rubiks3.SOLVED)
            self.assertEqual(row['candidate_solved'],
                             rubiks3.apply(row['state'], row['candidate_moves']) == rubiks3.SOLVED)
            self.assertEqual(row['candidate_move_count'], len(row['candidate_moves']))
            self.assertTrue(0 <= row['joint_features_covered'] <= 96)
            self.assertFalse(row['optimality_proven'])
            if row['candidate_paused']:
                self.assertEqual(row['candidate_failure'], 'paused_compute_budget')
                self.assertEqual(row['candidate_pause_checkpoint']['route'],
                                 row['candidate_moves'])

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            experiment(train_seeds=[1], test_seeds=[1])


if __name__ == '__main__':
    unittest.main()

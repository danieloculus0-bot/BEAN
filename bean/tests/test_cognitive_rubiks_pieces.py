"""Tests for native learned cubie subgoals and honest full-cube failures."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet import rubiks3
from experiments.cognitive_gauntlet.rubiks3_pieces import (
    experiment, local_reward, observed_edges, piece_features,
    policy_solve_pieces, train_pieces,
)
from experiments.cognitive_gauntlet.rubiks3_sponge import collect_states, _digest


class PieceSubgoalTests(unittest.TestCase):
    def test_stable_piece_identity_and_legal_state_transfer(self):
        home = piece_features(rubiks3.SOLVED)
        self.assertEqual(len(home), 20)
        self.assertEqual({d for _, _, d in home}, {0})
        ids = tuple(identity for identity, _, _ in home)
        for move in rubiks3.MOVES:
            with self.subTest(move=move):
                moved = piece_features(rubiks3.turn(rubiks3.SOLVED, move))
                self.assertEqual(ids, tuple(identity for identity, _, _ in moved))
                self.assertTrue(any(distance > 0 for _, _, distance in moved))

    def test_subgoal_reward_includes_progress_and_damage(self):
        self.assertEqual(local_reward(2, 1), .05)
        self.assertEqual(local_reward(1, 2), -.05)
        self.assertEqual(local_reward(1, 1), -.01)
        self.assertEqual(local_reward(1, 0), 1)
        self.assertEqual(local_reward(0, 1), -.2)
        self.assertEqual(local_reward(0, 0), 0)

    def test_train_piece_q_and_frozen_no_teacher_inference(self):
        states, _ = collect_states(range(8), (2, 3, 4))
        edges = observed_edges(states)
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'piece.db', actions=rubiks3.MOVES,
                               alpha=1, gamma=.9, epsilon=0, seed=19)
            try:
                receipt = train_pieces(learner, edges, epochs=2)
                self.assertEqual(receipt['piece_td_updates'], len(edges) * 20 * 2)
                self.assertGreater(len(learner.q), 0)
                frozen = _digest(learner.q)
                state = rubiks3.apply(rubiks3.SOLVED, rubiks3.scramble(21000, 20))
                with (patch.object(rubiks3, 'solve',
                                   side_effect=AssertionError('reference solver used')),
                      patch.object(rubiks3, 'scramble',
                                   side_effect=AssertionError('scramble leaked'))):
                    moves, info = policy_solve_pieces(learner, state)
                self.assertEqual(info['solved'],
                                 rubiks3.apply(state, moves) == rubiks3.SOLVED)
                self.assertEqual(_digest(learner.q), frozen)
            finally:
                learner.close()

    def test_illegal_cube_rejected(self):
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'piece.db', actions=rubiks3.MOVES)
            try:
                with self.assertRaises(ValueError):
                    policy_solve_pieces(learner, 'X' * 54)
                with self.assertRaises(ValueError):
                    piece_features('X' * 54)
            finally:
                learner.close()

    def test_matched_updates_disjoint_holdout_and_failure_receipts(self):
        result = experiment(train_seeds=range(8), test_seeds=range(21000, 21003),
                            train_lengths=(2, 3, 4), test_lengths=(3, 20), epochs=2)
        self.assertEqual(result['eligible_cases'] + result['excluded_count'], 6)
        self.assertEqual(result['eligible_cases'], len(result['cases']))
        self.assertEqual(result['excluded_count'], len(result['excluded']))
        self.assertEqual(result['td_updates_per_arm'],
                         result['candidate_training']['piece_td_updates'])
        self.assertEqual(result['twenty_turn_solved'],
                         sum(row['candidate_solved'] for row in result['cases']
                             if row['scramble_length'] == 20))
        for row in result['cases']:
            self.assertEqual(row['baseline_solved'],
                             rubiks3.apply(row['state'], row['baseline_moves']) == rubiks3.SOLVED)
            self.assertEqual(row['candidate_solved'],
                             rubiks3.apply(row['state'], row['candidate_moves']) == rubiks3.SOLVED)
            self.assertEqual(row['candidate_move_count'], len(row['candidate_moves']))
            self.assertTrue(0 <= row['piece_features_covered'] <= 20)
            self.assertFalse(row['optimality_proven'])

    def test_seed_overlap_rejected(self):
        with self.assertRaises(ValueError):
            experiment(train_seeds=[3], test_seeds=[3])


if __name__ == '__main__':
    unittest.main()

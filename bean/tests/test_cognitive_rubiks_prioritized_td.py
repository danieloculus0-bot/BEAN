"""Tests for BEAN-native prioritized cube TD, without external solution teachers."""
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet.rubiks3 import MOVES, SOLVED, apply, turn
from experiments.cognitive_gauntlet.rubiks3_symmetry import canonical
from experiments.cognitive_gauntlet.rubiks3_value_rollout import policy_solve_value_rollout
from experiments.cognitive_gauntlet.rubiks3_prioritized_td import (
    experiment, prioritized_replay, residual,
)


def tiny(**kwargs):
    config = dict(train_seeds=range(8), test_seeds=range(7000, 7002),
                  train_lengths=(2, 3), test_lengths=(3, 4, 20),
                  epochs=2, extra_updates=100)
    config.update(kwargs)
    return experiment(**config)


class PrioritizedCubeTDTests(unittest.TestCase):
    def test_bellman_residual_and_terminal_reward(self):
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'td.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                one = turn(SOLVED, 'U')
                edge = (one, MOVES.index("U'"), SOLVED)
                self.assertEqual(residual(learner, edge), 1.0)
                stats = prioritized_replay(learner, [edge], 5)
                self.assertEqual(stats['total_updates'], 5)
                self.assertEqual(stats['prioritized_updates'], 1)
                self.assertEqual(stats['matched_budget_filler_updates'], 4)
                self.assertEqual(learner.steps, 5)
                self.assertAlmostEqual(residual(learner, edge), 0.0)
                self.assertEqual(learner.q[learner.key(one)][MOVES.index("U'")], 1.0)
            finally:
                learner.close()

    def test_priorities_propagate_through_observed_legal_edges(self):
        one = turn(SOLVED, 'U')
        two = turn(one, 'F')
        # This is a legal transition graph, not a supplied inverse recipe.
        from experiments.cognitive_gauntlet.rubiks3_curriculum import edges_for
        edges = edges_for({SOLVED, one, two})
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'td.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                stats = prioritized_replay(learner, edges, 50)
                self.assertEqual(stats['total_updates'], 50)
                self.assertTrue(any(v > 0 for v in
                                    learner.q.get(learner.key(canonical(two)[0]), [])))
            finally:
                learner.close()

    def test_matched_training_and_all_negative_receipts(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / 'receipt.json'
            report = tiny(output=output)
            self.assertEqual(report, json.loads(output.read_text(encoding='utf-8')))
            self.assertEqual(report['baseline_td_steps'], report['candidate_td_steps'])
            self.assertEqual(report['extra_td_updates_per_arm'], 100)
            self.assertEqual(report['eligible_cases'] + report['excluded_count'], 6)
            self.assertEqual(len(report['cases']), report['eligible_cases'])
            self.assertEqual(len(report['excluded']), report['excluded_count'])
            self.assertEqual(report['candidate_solved'],
                             sum(row['candidate_solved'] for row in report['cases']))
            self.assertEqual(report['candidate_worse'],
                             sum(row['candidate_worse'] for row in report['cases']))
            self.assertEqual(report['module_sha256'], hashlib.sha256(
                Path(__import__('experiments.cognitive_gauntlet.rubiks3_prioritized_td',
                                fromlist=['experiment']).__file__).read_text(
                                    encoding='utf-8').encode('utf-8')).hexdigest())
            self.assertTrue(all(not row['candidate_solved'] or
                                apply(row['state'], row['candidate_moves']) == SOLVED
                                for row in report['cases']))

    def test_training_and_holdout_rotation_classes_disjoint(self):
        report = tiny()
        from experiments.cognitive_gauntlet.rubiks3_sponge import collect_states
        states, _ = collect_states(range(8), (2, 3))
        training = {canonical(s)[0] for s in states}
        self.assertTrue(all(row['canonical_state'] not in training
                            for row in report['cases']))
        self.assertEqual(len({row['canonical_state'] for row in report['cases']}),
                         len(report['cases']))

    def test_replay_is_deterministic_and_no_solver_required_at_inference(self):
        first, second = tiny(), tiny()
        self.assertEqual(first['sha256'], second['sha256'])
        one = turn(SOLVED, 'U')
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'td.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                normalized, faces = canonical(one)
                prioritized_replay(learner, [(normalized, MOVES.index(faces['U'] + "'"),
                                              canonical(SOLVED)[0])], 5)
                # No reference solve, scramble generator, or inverse recipe may
                # be consulted by the policy at inference.
                with patch('experiments.cognitive_gauntlet.rubiks3.solve',
                           side_effect=AssertionError('reference solver leaked')), \
                     patch('experiments.cognitive_gauntlet.rubiks3.invert',
                           side_effect=AssertionError('inverse recipe leaked')), \
                     patch('experiments.cognitive_gauntlet.rubiks3.scramble',
                           side_effect=AssertionError('scramble leaked')):
                    route, info = policy_solve_value_rollout(learner, one)
                self.assertEqual(info['solved'], apply(one, route) == SOLVED)
            finally:
                learner.close()

    def test_invalid_budgets_and_overlapping_seeds(self):
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'td.db', actions=MOVES)
            try:
                with self.assertRaises(ValueError):
                    prioritized_replay(learner, [], 1)
                with self.assertRaises(ValueError):
                    prioritized_replay(learner, [], -1)
            finally:
                learner.close()
        with self.assertRaises(ValueError):
            tiny(test_seeds=(0, 7000))


if __name__ == '__main__':
    unittest.main()

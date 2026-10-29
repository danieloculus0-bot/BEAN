"""Independent tests for BEAN-native learned-value backups, not cubejs solving."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet.rubiks3 import MOVES, SOLVED, apply, scramble, turn
from experiments.cognitive_gauntlet.rubiks3_sponge import collect_states, _digest
from experiments.cognitive_gauntlet.rubiks3_symmetry import learn_symmetric, canonical
from experiments.cognitive_gauntlet.rubiks3_value_rollout import (
    experiment, policy_solve_value_rollout,
)


class ValueRolloutTests(unittest.TestCase):
    def test_native_two_transition_value_transfer_without_teacher(self):
        states, _ = collect_states(range(12), (2, 3, 4))
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'policy.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                learn_symmetric(learner, states, epochs=8)
                before = _digest(learner.q)
                for seed in (100, 101, 102):
                    state = apply(SOLVED, scramble(seed, 5))
                    with (patch('experiments.cognitive_gauntlet.rubiks3_value_rollout.solve',
                                side_effect=AssertionError('reference leaked into inference')),
                          patch('experiments.cognitive_gauntlet.rubiks3_value_rollout.scramble',
                                side_effect=AssertionError('scramble leaked into inference'))):
                        route, info = policy_solve_value_rollout(learner, state)
                    self.assertEqual(info['solved'], apply(state, route) == SOLVED)
                self.assertEqual(before, _digest(learner.q))
            finally:
                learner.close()

    def test_short_learned_route_replays(self):
        start = turn(SOLVED, 'R')
        states = {SOLVED, start, turn(start, 'U')}
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'policy.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                learn_symmetric(learner, states, epochs=8)
                route, info = policy_solve_value_rollout(learner, start)
                self.assertTrue(info['solved'])
                self.assertEqual(apply(start, route), SOLVED)
                self.assertEqual(len(route), 1)
            finally:
                learner.close()

    def test_paired_holdout_and_complete_failure_receipts(self):
        args = dict(train_seeds=range(12), test_seeds=range(700, 703),
                    train_lengths=(2, 3, 4), test_lengths=(3, 4, 20),
                    epochs=6)
        with TemporaryDirectory() as tmp:
            first = experiment(output=Path(tmp) / 'receipts.json', **args)
            second = experiment(**args)
            self.assertEqual(first, second)
            self.assertTrue((Path(tmp) / 'receipts.json').exists())
            self.assertEqual(len(first['cases']) + len(first['excluded']), 9)
            self.assertEqual(first['eligible_cases'], len(first['cases']))
            self.assertEqual(first['excluded_count'], len(first['excluded']))
            self.assertEqual(first['baseline_solved'],
                             sum(c['baseline_solved'] for c in first['cases']))
            self.assertEqual(first['candidate_solved'],
                             sum(c['candidate_solved'] for c in first['cases']))
            self.assertTrue(any(c['scramble_length'] == 20 for c in first['cases']))
            normalized = [c['canonical_state'] for c in first['cases']]
            self.assertEqual(len(normalized), len(set(normalized)))
            for case in first['cases']:
                self.assertEqual(case['canonical_state'], canonical(case['state'])[0])
                self.assertEqual(case['baseline_solved'],
                                 apply(case['state'], case['baseline_moves']) == SOLVED)
                self.assertEqual(case['candidate_solved'],
                                 apply(case['state'], case['candidate_moves']) == SOLVED)

    def test_invalid_cube_and_invalid_horizon_rejected(self):
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'policy.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                with self.assertRaises(ValueError):
                    policy_solve_value_rollout(learner, SOLVED, backup_depth=2)
                with self.assertRaises(ValueError):
                    policy_solve_value_rollout(learner, SOLVED[:-1])
            finally:
                learner.close()

    def test_train_holdout_seed_overlap_rejected(self):
        with self.assertRaises(ValueError):
            experiment(train_seeds=[1], test_seeds=[1])


if __name__ == '__main__':
    unittest.main()

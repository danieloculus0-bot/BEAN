"""Exact-source independent checks for 24-rotation BEAN SpongeTD transfer."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet.rubiks3 import MOVES, SOLVED, apply, scramble, turn
from experiments.cognitive_gauntlet.rubiks3_symmetry import (
    TRANSFORMS, canonical, experiment, learn_symmetric,
    policy_solve_symmetric, transform,
)
from experiments.cognitive_gauntlet.rubiks3_sponge import collect_states, _digest


class SymmetryCubeTests(unittest.TestCase):
    def test_all_24_rotations_preserve_solved_and_move_equivariance(self):
        self.assertEqual(len(TRANSFORMS), 24)
        for seed in (0, 1, 17, 321):
            state = apply(SOLVED, scramble(seed, 20))
            for rotation, (_, faces) in enumerate(TRANSFORMS):
                self.assertEqual(transform(SOLVED, rotation), SOLVED)
                for move in MOVES:
                    transformed = transform(turn(state, move), rotation)
                    rotated_action = faces[move[0]] + move[1:]
                    self.assertEqual(transformed,
                                     turn(transform(state, rotation), rotated_action))

    def test_canonicalization_is_rotation_invariant(self):
        for seed in (2, 8, 43):
            state = apply(SOLVED, scramble(seed, 12))
            canonical_state, _ = canonical(state)
            for rotation in range(24):
                self.assertEqual(canonical(transform(state, rotation))[0], canonical_state)

    def test_policy_learns_terminal_reward_without_solution_recipe(self):
        states, _ = collect_states(range(20), (2, 3, 4))
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp)/'policy.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                training = learn_symmetric(learner, states, epochs=8)
                self.assertGreater(training['td_updates'], 0)
                self.assertTrue(any(max(v) > 0 for v in learner.q.values()))
                before = _digest(learner.q)
                for seed in (1000, 1001, 1002):
                    state = apply(SOLVED, scramble(seed, 5))
                    moves, result = policy_solve_symmetric(learner, state)
                    self.assertEqual(result['solved'], apply(state, moves) == SOLVED)
                self.assertEqual(before, _digest(learner.q))
            finally:
                learner.close()

    def test_frozen_paired_holdout_and_receipts(self):
        params = dict(train_seeds=range(30), test_seeds=range(800, 804),
                      train_lengths=(2, 3, 4), test_lengths=(3, 4, 5, 20), epochs=8)
        with TemporaryDirectory() as tmp:
            a = experiment(output=Path(tmp)/'results.json', **params)
            b = experiment(**params)
            self.assertEqual(a, b)
            self.assertEqual(len(a['cases']) + len(a['excluded']), 16)
            self.assertEqual(a['eligible_cases'], len(a['cases']))
            self.assertEqual(a['excluded_count'], len(a['excluded']))
            self.assertEqual(a['twenty_turn_cases'],
                             sum(c['scramble_length'] == 20 for c in a['cases']))
            self.assertEqual(a['twenty_turn_solved'],
                             sum(c['candidate_solved'] for c in a['cases']
                                 if c['scramble_length'] == 20))
            self.assertTrue((Path(tmp)/'results.json').is_file())
            self.assertTrue(any(c['scramble_length'] == 20 for c in a['cases']))
            # Independent holdout units are rotation classes, not just strings.
            classes = [canonical(c['state'])[0] for c in a['cases']]
            self.assertEqual(len(classes), len(set(classes)))
            self.assertEqual(classes, [c['canonical_state'] for c in a['cases']])
            self.assertTrue(all(c['canonical_state'] == canonical(c['state'])[0]
                                for c in a['excluded']))
            self.assertTrue(all(c['reason'] in ('training_symmetry_overlap',
                                               'duplicate_holdout_symmetry_class')
                                for c in a['excluded']))
            for c in a['cases']:
                self.assertEqual(c['baseline_solved'], apply(c['state'], c['baseline_moves']) == SOLVED)
                self.assertEqual(c['candidate_solved'], apply(c['state'], c['candidate_moves']) == SOLVED)
                if c['candidate_matches_proven_optimum']:
                    self.assertTrue(c['reference_proven_optimal'])
                    self.assertEqual(len(c['candidate_moves']), len(c['reference_moves']))

    def test_predeclared_frozen_cohort_improves_without_full_cube_claim(self):
        result = experiment()
        self.assertEqual(len(result['cases']) + len(result['excluded']), 50)
        self.assertGreater(result['candidate_solved'], result['baseline_solved'])
        self.assertEqual(result['candidate_worse'], 0)
        self.assertEqual(result['candidate_solved'],
                         result['candidate_matches_proven_optimum'])
        twenty = [c for c in result['cases'] if c['scramble_length'] == 20]
        self.assertEqual(len(twenty), 10)
        self.assertTrue(all(not c['candidate_solved'] for c in twenty))

    def test_inference_uses_learned_policy_without_reference_or_scramble(self):
        # Training comes only from a tiny legal transition graph and terminal
        # reward. The inference path must not be able to call a teacher,
        # scramble generator, or the baseline search routine.
        start = turn(SOLVED, 'R')
        states = {SOLVED, start, turn(start, 'U')}
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp)/'policy.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                learn_symmetric(learner, states, epochs=8)
                with (patch('experiments.cognitive_gauntlet.rubiks3_symmetry.solve',
                            side_effect=AssertionError('reference solver called')),
                      patch('experiments.cognitive_gauntlet.rubiks3_symmetry.scramble',
                            side_effect=AssertionError('scramble leaked')),
                      patch('experiments.cognitive_gauntlet.rubiks3_sponge.solve',
                            side_effect=AssertionError('baseline solver called'))):
                    moves, report = policy_solve_symmetric(learner, start)
                self.assertTrue(report['solved'])
                self.assertEqual(apply(start, moves), SOLVED)
                self.assertEqual(len(moves), 1)
            finally:
                learner.close()

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            experiment(train_seeds=[7], test_seeds=[7])


if __name__ == '__main__':
    unittest.main()

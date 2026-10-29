"""Tests for legal-cubie hotter/colder feedback and matched BEAN learning."""
import unittest
from unittest.mock import patch

from experiments.cognitive_gauntlet import rubiks3
from experiments.cognitive_gauntlet.rubiks3_symmetry import transform
from experiments.cognitive_gauntlet.rubiks3_temperature import (
    PIECE_TABLES, experiment, hotter_colder, piece_distances,
    shaped_reward, temperature,
)


class RubiksTemperatureTests(unittest.TestCase):
    def test_piece_tables_cover_all_cubie_configurations(self):
        self.assertEqual(len(PIECE_TABLES), 20)
        self.assertTrue(all(len(table[1]) == 24 for table in PIECE_TABLES.values()))
        self.assertEqual(piece_distances(rubiks3.SOLVED), (0, 0))
        self.assertEqual(temperature(rubiks3.SOLVED), 0)
        for move in rubiks3.MOVES:
            with self.subTest(move=move):
                state = rubiks3.turn(rubiks3.SOLVED, move)
                self.assertLess(temperature(state), 0)
                self.assertGreater(hotter_colder(state, rubiks3.SOLVED), 0)
                self.assertLess(hotter_colder(rubiks3.SOLVED, state), 0)

    def test_temperature_is_rotation_equivariant(self):
        state = rubiks3.apply(rubiks3.SOLVED, ['R', 'U', 'F2', "L'"])
        for rotation in range(24):
            with self.subTest(rotation=rotation):
                self.assertEqual(piece_distances(transform(state, rotation)),
                                 piece_distances(state))

    def test_discounted_potential_telescope(self):
        start = rubiks3.apply(rubiks3.SOLVED, ['R', 'U', 'F'])
        states = [start]
        for move in ("F'", "U'", "R'"):
            states.append(rubiks3.turn(states[-1], move))
        self.assertEqual(states[-1], rubiks3.SOLVED)
        gamma = .9
        discounted_extra = 0
        for t, (before, after) in enumerate(zip(states, states[1:])):
            original = 1.0 if after == rubiks3.SOLVED else 0.0
            discounted_extra += gamma ** t * (shaped_reward(before, after, gamma) - original)
        self.assertAlmostEqual(discounted_extra, -temperature(start), places=10)

    def test_rejects_impossible_states(self):
        with self.assertRaises(ValueError):
            temperature('X' * 54)
        with self.assertRaises(ValueError):
            shaped_reward('X' * 54, rubiks3.SOLVED)
        with self.assertRaises(ValueError):
            shaped_reward(rubiks3.SOLVED, rubiks3.SOLVED, 1.1)

    def test_disjoint_holdout_complete_receipts_and_matched_updates(self):
        result = experiment(train_seeds=range(10), test_seeds=range(13000, 13003),
                            train_lengths=(2, 3, 4), test_lengths=(3, 4, 20), epochs=2)
        self.assertEqual(result['baseline_training']['td_updates'],
                         result['candidate_training']['td_updates'])
        self.assertEqual(result['eligible_cases'] + result['excluded_count'], 9)
        self.assertEqual(result['eligible_cases'], len(result['cases']))
        self.assertEqual(result['excluded_count'], len(result['excluded']))
        for case in result['cases']:
            self.assertEqual(rubiks3.apply(case['state'], case['candidate_moves']) == rubiks3.SOLVED,
                             case['candidate_solved'])
            self.assertEqual(rubiks3.apply(case['state'], case['baseline_moves']) == rubiks3.SOLVED,
                             case['baseline_solved'])
            self.assertEqual(case['candidate_move_count'], len(case['candidate_moves']))
            self.assertFalse(case['optimality_proven'])
        self.assertEqual(result['candidate_better'],
                         sum(c['candidate_solved'] and not c['baseline_solved'] for c in result['cases']))

    def test_potential_corrected_value_interpretation(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from bean.optimization.sponge_td import SpongeTD
        from experiments.cognitive_gauntlet.rubiks3_symmetry import canonical, MOVE_INDEX
        from experiments.cognitive_gauntlet.rubiks3_temperature import _unshaped_action
        state = rubiks3.turn(rubiks3.SOLVED, 'R')
        normalized, faces = canonical(state)
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'test.db', actions=rubiks3.MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                values = learner.values(normalized)
                values[MOVE_INDEX[faces["R"] + "'"]] = .8 - temperature(state)
                self.assertAlmostEqual(_unshaped_action(learner, state, "R'"), .8)
            finally:
                learner.close()

    def test_corrected_policy_receipts_on_separate_validation(self):
        result = experiment(train_seeds=range(10), test_seeds=range(15000, 15003),
                            train_lengths=(2, 3, 4), test_lengths=(3, 4, 20),
                            epochs=2, controller='unshaped')
        self.assertEqual(result['controller'], 'unshaped')
        self.assertEqual(result['eligible_cases'] + result['excluded_count'], 9)
        self.assertEqual(result['baseline_training']['td_updates'],
                         result['candidate_training']['td_updates'])
        self.assertEqual(result['twenty_turn_solved'],
                         sum(c['candidate_solved'] for c in result['cases']
                             if c['scramble_length'] == 20))

    def test_no_reference_solver_or_scramble_at_inference(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from bean.optimization.sponge_td import SpongeTD
        from experiments.cognitive_gauntlet.rubiks3_value_rollout import policy_solve_value_rollout
        state = rubiks3.turn(rubiks3.SOLVED, 'R')
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'test.db', actions=rubiks3.MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                with (patch.object(rubiks3, 'solve', side_effect=AssertionError('reference solver called')),
                      patch.object(rubiks3, 'scramble', side_effect=AssertionError('scramble called'))):
                    route, info = policy_solve_value_rollout(learner, state)
                self.assertEqual(info['solved'], rubiks3.apply(state, route) == rubiks3.SOLVED)
            finally:
                learner.close()


if __name__ == '__main__':
    unittest.main()

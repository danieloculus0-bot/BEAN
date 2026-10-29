"""Reproducibility and isolation tests for native cube TD curriculum."""
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet.rubiks3 import MOVES, SOLVED, apply, turn
from experiments.cognitive_gauntlet.rubiks3_symmetry import canonical, learn_symmetric
from experiments.cognitive_gauntlet.rubiks3_value_rollout import policy_solve_value_rollout
from experiments.cognitive_gauntlet.rubiks3_curriculum import (
    curriculum_lengths, experiment,
)


def tiny(**kwargs):
    params = dict(train_seeds=range(8), validation_seeds=range(100, 102),
                  expansion_seeds=range(200, 204), test_seeds=range(500, 502),
                  train_lengths=(2, 3), validation_lengths=(3, 4, 20),
                  test_lengths=(3, 4, 20), epochs=4, extra_updates=120)
    params.update(kwargs)
    return experiment(**params)


class CurriculumTests(unittest.TestCase):
    def test_validation_controls_exploration_not_move_limit(self):
        rows = [{'scramble_length': 3, 'solved': True},
                {'scramble_length': 4, 'solved': False},
                {'scramble_length': 20, 'solved': False}]
        self.assertEqual(curriculum_lengths(rows), (5, 10))
        self.assertEqual(curriculum_lengths([]), ())
        with self.assertRaises(ValueError):
            curriculum_lengths(rows, ceiling=0)

    def test_seed_overlap_rejected(self):
        with self.assertRaises(ValueError):
            tiny(validation_seeds=[0])
        with self.assertRaises(ValueError):
            tiny(test_seeds=[500, 500])

    def test_deterministic_paired_update_budget_and_full_replay(self):
        a, b = tiny(), tiny()
        self.assertEqual(a, b)
        self.assertEqual(a['baseline_td_steps'], a['candidate_td_steps'])
        self.assertEqual(len(a['cases']) + len(a['excluded']), 6)
        self.assertEqual(a['eligible_cases'], len(a['cases']))
        self.assertEqual(a['excluded_count'], len(a['excluded']))
        self.assertEqual(a['baseline_solved'], sum(c['baseline_solved'] for c in a['cases']))
        self.assertEqual(a['candidate_solved'], sum(c['candidate_solved'] for c in a['cases']))
        self.assertTrue(any(c['scramble_length'] == 20 for c in a['cases']))
        for case in a['cases']:
            self.assertEqual(case['baseline_solved'],
                             apply(case['state'], case['baseline_moves']) == SOLVED)
            self.assertEqual(case['candidate_solved'],
                             apply(case['state'], case['candidate_moves']) == SOLVED)
            self.assertFalse(case['optimality_proven'])
        classes = [c['canonical_state'] for c in a['cases']]
        self.assertEqual(len(classes), len(set(classes)))
        self.assertFalse(set(classes) & {c['canonical_state'] for c in a['validation']})

    def test_solver_and_scramble_blocked_during_native_inference(self):
        state = turn(SOLVED, 'R')
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp) / 'q.db', actions=MOVES,
                               alpha=1, gamma=.9, epsilon=0)
            try:
                learn_symmetric(learner, {SOLVED, state}, epochs=6)
                with (patch('experiments.cognitive_gauntlet.rubiks3.solve',
                            side_effect=AssertionError('reference solver called')),
                      patch('experiments.cognitive_gauntlet.rubiks3_value_rollout.scramble',
                            side_effect=AssertionError('scramble leaked'))):
                    moves, meta = policy_solve_value_rollout(learner, state)
                self.assertTrue(meta['solved'])
                self.assertEqual(apply(state, moves), SOLVED)
            finally:
                learner.close()

    def test_json_receipts_include_all_negative_cases(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cases.json'
            report = tiny(output=path)
            self.assertEqual(report, json.loads(path.read_text(encoding='utf-8')))
            source = Path(__import__('experiments.cognitive_gauntlet.rubiks3_curriculum',
                                     fromlist=['experiment']).__file__)
            normalized = source.read_text(encoding='utf-8').encode('utf-8')
            self.assertEqual(report['module_sha256'], hashlib.sha256(normalized).hexdigest())
            self.assertEqual(len(report['cases']) + len(report['excluded']), 6)


if __name__ == '__main__':
    unittest.main()

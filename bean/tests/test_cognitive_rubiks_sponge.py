"""BEAN SpongeTD cube policy tests, independent replay and failure retention."""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from bean.optimization.sponge_td import SpongeTD
from experiments.cognitive_gauntlet.rubiks3 import SOLVED, MOVES, apply, scramble
from experiments.cognitive_gauntlet.rubiks3_sponge import (
    collect_states, learn_policy, policy_solve, experiment, _digest)


class SpongeCubeTests(unittest.TestCase):
    def test_terminal_reward_creates_learned_action_values(self):
        states, _ = collect_states(range(12), (2, 3))
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp)/'td.db', actions=MOVES, alpha=1, gamma=.9, epsilon=0)
            info = learn_policy(learner, states, epochs=10)
            self.assertGreater(info['td_updates'], 0)
            self.assertTrue(any(max(v)>0 for v in learner.q.values()))
            self.assertTrue(policy_solve(learner, SOLVED)[1]['solved'])
            learner.close()

    def test_unseen_seed_no_scramble_trace_at_policy_interface(self):
        a = experiment(train_seeds=range(30), test_seeds=range(700, 704),
                       train_lengths=(2, 3, 4), test_lengths=(3, 4, 20),
                       epochs=8, reference_depth=4)
        b = experiment(train_seeds=range(30), test_seeds=range(700, 704),
                       train_lengths=(2, 3, 4), test_lengths=(3, 4, 20),
                       epochs=8, reference_depth=4)
        self.assertEqual(a, b)
        self.assertEqual(12, len(a['cases']) + len(a['excluded']))
        self.assertTrue(all(not c['training_state_seen'] for c in a['cases']))
        self.assertTrue(any(not c['policy_solved'] for c in a['cases']))
        for c in a['cases']:
            self.assertEqual(c['policy_solved'], apply(c['state'], c['policy_moves']) == SOLVED)
        self.assertEqual(a['training']['td_updates'],
                         a['training']['legal_sampled_edges'] * a['training']['epochs'])

    def test_default_frozen_holdout_and_checkpoint_restart(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)/'case-receipts.json'
            result = experiment(output=out)
            self.assertEqual(len(result['cases']) + len(result['excluded']), 50)
            self.assertTrue(all(not c['training_state_seen'] for c in result['cases']))
            self.assertGreater(result['policy_solved'], 0)
            self.assertTrue(any(c['scramble_length'] == 20 and not c['policy_solved']
                                for c in result['cases']))
            self.assertTrue(out.is_file())
            learner = SpongeTD(out.with_suffix('.sqlite3'), actions=MOVES,
                               alpha=1.0, gamma=0.9, epsilon=0.0, seed=19)
            self.assertEqual(result['policy_q_sha256'], _digest(learner.q))
            for case in result['cases']:
                moves, info = policy_solve(learner, case['state'])
                self.assertEqual(moves, case['policy_moves'])
                self.assertEqual(info['solved'], case['policy_solved'])
            learner.close()

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            experiment(train_seeds=[1], test_seeds=[1])

    def test_policy_failure_is_not_reference_rescued(self):
        with TemporaryDirectory() as tmp:
            learner = SpongeTD(Path(tmp)/'td.db', actions=MOVES, alpha=1, gamma=.9, epsilon=0)
            state = apply(SOLVED, scramble(55, 20))
            route, info = policy_solve(learner, state)
            self.assertEqual(route, [])
            self.assertFalse(info['solved'])
            self.assertEqual(info['failure'], 'no_positive_learned_action')
            self.assertEqual(learner.q, {})
            learner.close()

if __name__ == '__main__': unittest.main()

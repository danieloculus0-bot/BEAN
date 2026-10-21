"""Independent Vaultbreaker experiment checks, incl. real NN training and ledger replay."""
import copy
import tempfile
import unittest
from pathlib import Path
from indexed_ledger import IndexedLedger
from vaultbreaker import (
    CODES, MAX_TURNS, TinyNeuralPolicy, archive_episode, experiment, feedback,
    initial_board, play, replay_archive, reward, verify_trace,
)


class VaultTests(unittest.TestCase):
    def test_feedback_duplicates_and_exact(self):
        self.assertEqual(feedback((0,0,1,1),(0,1,0,2)),(1,2))
        self.assertEqual(feedback((1,1,1,1),(1,1,1,1)),(4,0))
        self.assertEqual(feedback((1,1,1,1),(2,2,2,2)),(0,0))

    def test_fixed_bruteforce_solves_sampled_codes(self):
        for secret in CODES[::41]:
            board=initial_board()
            trace=play(secret,None,board,episode=1)
            verify_trace(trace)
            self.assertTrue(trace['won'])
            self.assertLessEqual(trace['turns'],MAX_TURNS)

    def test_no_reward_farming_from_more_steps(self):
        slow=reward(1296,36,False,0)+reward(36,1,True,0)
        fast=reward(1296,1,True,0)
        self.assertAlmostEqual(fast-slow,9,places=4)

    def test_policy_reads_scoreboard_and_exact_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy=TinyNeuralPolicy(11)
            board=initial_board()
            trace=play(CODES[442],policy,board,episode=0,train=True)
            verify_trace(trace)
            ledger=IndexedLedger(tmp)
            archive_episode(ledger,'vault-000',trace)
            ledger.rebuild()
            self.assertEqual(replay_archive(ledger,'vault-000'),trace)
            self.assertTrue(all('scoreboard_seen' in m and 'reward' in m
                                for m in trace['moves']))
            self.assertGreater(policy.updates,0)
            ledger.cache.unlink()
            ledger.rebuild()
            self.assertEqual(replay_archive(ledger,'vault-000'),trace)

    def test_mutated_score_or_reward_rejected(self):
        trace=play(CODES[672],TinyNeuralPolicy(5),initial_board(),episode=10,train=True)
        broken=copy.deepcopy(trace)
        broken['moves'][0]['reward']+=10
        with self.assertRaisesRegex(AssertionError,'oracle replay diverged'):
            verify_trace(broken)
        broken=copy.deepcopy(trace)
        broken['moves'][0]['scoreboard_seen']['reward_total']=9999
        with self.assertRaisesRegex(AssertionError,'scoreboard receipt mismatch'):
            verify_trace(broken)

    def test_training_and_unseen_holdout_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome=experiment(Path(tmp),training=6,holdout=6,seed=42)
            self.assertNotEqual(outcome['initial_weights_sha256'],
                                outcome['saved_weights_sha256'])
            self.assertEqual(outcome['saved_weights_sha256'],
                             outcome['reloaded_weights_sha256'])
            self.assertEqual(outcome['neural_updates'],
                             outcome['training']['scoreboard']['total_guesses'])
            self.assertEqual(outcome['fixed_bruteforce']['replayed_games'],6)
            self.assertEqual(outcome['untrained_neural']['replayed_games'],6)
            self.assertEqual(outcome['trained_neural']['replayed_games'],6)


if __name__=='__main__':
    unittest.main()

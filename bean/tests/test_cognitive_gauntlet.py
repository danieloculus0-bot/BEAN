import unittest
from experiments.cognitive_gauntlet.paired_baseline import score


class TestPaired(unittest.TestCase):
    def test_repeatable(self):
        self.assertEqual(score(7, 20), score(7, 20))

    def test_full_history(self):
        self.assertEqual(len(score(7, 20)['cases']), 20)

    def test_no_external_wins(self):
        self.assertEqual(score(7, 20)['external_agents_executed'], [])

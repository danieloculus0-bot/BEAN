"""Synthetic controls: duplicate evidence must not inflate transfer confidence.

Research-only, no BEAN runtime integration or new memory backend.
Run: python -m unittest -v test_evidence_independence.py
"""
import math
import unittest


def estimate(receipts, deduplicate=True):
    """Laplace-smoothed observed success rate, grouped by independent trial ID.

    A conflicting duplicate is rejected rather than silently selecting a label.
    This is an illustrative statistic, not calibrated probability of transfer.
    """
    trials = {}
    for trial, success in receipts:
        if not isinstance(trial, str) or not trial:
            raise ValueError('missing independent trial identifier')
        if type(success) is not bool:
            raise ValueError('outcome must be observed boolean')
        if deduplicate and trial in trials and trials[trial] != success:
            raise ValueError('conflicting evidence for one trial')
        trials[trial] = success if deduplicate else trials.get(trial, []) + [success]
    observations = list(trials.values()) if deduplicate else [v for group in trials.values() for v in group]
    wins = sum(observations)
    return (wins + 1) / (len(observations) + 2), len(observations)


class EvidenceIndependenceTests(unittest.TestCase):
    def test_duplicate_positive_does_not_create_new_trials(self):
        base = [('source-A', True), ('source-B', False)]
        repeated = base + [('source-A', True)] * 200
        self.assertEqual(estimate(base), estimate(repeated))
        naive, count = estimate(repeated, deduplicate=False)
        self.assertEqual(count, 202)
        self.assertGreater(naive, 0.98)

    def test_independent_negative_evidence_changes_estimate(self):
        original = [('source-A', True), ('source-B', True)]
        revised = original + [('source-C', False), ('source-D', False)]
        self.assertEqual(estimate(original), (0.75, 2))
        self.assertEqual(estimate(revised), (0.5, 4))

    def test_conflicting_revisions_are_not_merged_as_independent(self):
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            estimate([('trial-1', True), ('trial-1', False)])

    def test_missing_provenance_and_unobserved_outcomes_rejected(self):
        for case in [[('', True)], [('trial-1', None)], [('trial-1', 1)]]:
            with self.subTest(case=case), self.assertRaises(ValueError):
                estimate(case)

    def test_restart_replay_order_and_duplicate_invariance(self):
        history = [('a', True), ('b', False), ('c', False), ('a', True)]
        restored = list(reversed(history))
        self.assertEqual(estimate(history), estimate(restored))
        self.assertEqual(estimate(history), estimate(history + history))


if __name__ == '__main__':
    unittest.main()

"""Synthetic research control: known label propensities versus missing-not-at-random.

Not a deployed BEAN calibration policy. True propensities are privileged simulation
information; real missing-label mechanisms are not generally identifiable.
"""
import hashlib
import json
import random
import unittest


def trial(seed, *, shifted=True, n=4000, p_correct=0.9, p_wrong=0.08):
    rng = random.Random(seed)
    rows = []
    for t in range(n):
        error = rng.random() < (0.8 if shifted and t >= n // 2 else 0.15)
        observed = rng.random() < (p_wrong if error else p_correct)
        rows.append((t, int(error), int(observed)))
    tail = rows[n // 2:]
    labeled = [r for r in tail if r[2]]
    naive = sum(r[1] for r in labeled) / len(labeled)
    weighted_error = sum(r[1] / (p_wrong if r[1] else p_correct) for r in labeled)
    weighted_total = sum(1 / (p_wrong if r[1] else p_correct) for r in labeled)
    return {
        'true_error': sum(r[1] for r in tail) / len(tail),
        'naive_error': naive,
        'oracle_ipw_error': weighted_error / weighted_total,
        'labeled': len(labeled),
        'total': len(tail),
        'sha256': hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest(),
    }


class PropensityControls(unittest.TestCase):
    def test_shifted_heldout_seeds(self):
        results = [trial(s) for s in range(100, 120)]
        naive = sum(abs(x['naive_error'] - x['true_error']) for x in results) / len(results)
        corrected = sum(abs(x['oracle_ipw_error'] - x['true_error']) for x in results) / len(results)
        self.assertLess(corrected, naive / 3)
        self.assertGreater(naive, 0.4)

    def test_stationary_control(self):
        results = [trial(s, shifted=False) for s in range(120, 140)]
        self.assertLess(sum(abs(x['oracle_ipw_error'] - x['true_error']) for x in results) / len(results), 0.04)

    def test_unbiased_feedback_control(self):
        results = [trial(s, p_correct=0.5, p_wrong=0.5) for s in range(140, 150)]
        self.assertTrue(all(abs(x['naive_error'] - x['oracle_ipw_error']) < 1e-12 for x in results))

    def test_replay_and_budget(self):
        a = trial(77)
        self.assertEqual(a, trial(77))
        self.assertEqual(a['total'], 2000)
        self.assertEqual(len(a['sha256']), 64)
        self.assertNotEqual(a['sha256'], trial(78)['sha256'])

    def test_unobserved_propensities_not_identifiable(self):
        visible = [(1, 1), (0, 1), (None, 0)]
        worlds = [[1, 0, 0], [1, 0, 1]]
        self.assertEqual([x for x in visible if x[1]], [(1, 1), (0, 1)])
        self.assertNotEqual(sum(worlds[0]), sum(worlds[1]))


if __name__ == '__main__':
    unittest.main()

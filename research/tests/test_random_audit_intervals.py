"""Synthetic audit precision control: uncertainty must accompany sparse audits.

Research only, not a BEAN runtime policy. Wilson intervals assume independently
randomized audits, uncorrupted labels and fixed evaluation windows.
"""
import math
import random
import unittest


def wilson(errors, audited, z=1.959963984540054):
    if audited == 0:
        return (0.0, 1.0)
    if not (0 <= errors <= audited):
        raise ValueError("invalid audit counts")
    p = errors / audited
    d = 1 + z*z/audited
    c = (p + z*z/(2*audited))/d
    h = z*math.sqrt(p*(1-p)/audited + z*z/(4*audited*audited))/d
    return (max(0.0, c-h if errors else 0.0), min(1.0, c+h))


def trial(seed, rate, n=4000, shifted=True):
    rng = random.Random(seed)
    errors = audited = 0
    for t in range(n):
        # Frozen prediction fails after hidden deterministic reversal.
        error = int(shifted and t >= n//2)
        if rng.random() < rate:
            audited += 1
            errors += error
    return errors, audited, wilson(errors, audited)


class AuditIntervalControls(unittest.TestCase):
    def test_zero_audit_cannot_certify_accuracy(self):
        self.assertEqual(trial(9, 0)[2], (0.0, 1.0))

    def test_sparse_audits_wider_than_dense(self):
        sparse = trial(22, .01)
        dense = trial(22, .25)
        self.assertLess(sparse[1], dense[1])
        self.assertGreater(sparse[2][1]-sparse[2][0], dense[2][1]-dense[2][0])

    def test_heldout_seed_coverage_shift_and_stationary(self):
        for shifted in (False, True):
            truth = .5 if shifted else 0.0
            covered = 0
            for seed in range(100, 140):
                lo, hi = trial(seed, .12, shifted=shifted)[2]
                covered += lo <= truth <= hi
            self.assertGreaterEqual(covered, 35)

    def test_determinism_and_invalid_counts(self):
        self.assertEqual(trial(777, .12), trial(777, .12))
        with self.assertRaises(ValueError):
            wilson(3, 2)

    def test_coverage_is_not_guaranteed_on_every_seed(self):
        self.assertEqual(wilson(0, 0), (0.0, 1.0))
        self.assertLess(wilson(0, 100)[1], .05)


if __name__ == "__main__":
    unittest.main()

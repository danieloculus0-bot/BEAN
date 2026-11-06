"""Anytime-valid audit bounds under repeated inspection.

Synthetic independent Bernoulli audit outcomes only. A fixed-time Wilson interval
is not a confidence sequence. This module compares it with a conservative
time-uniform Hoeffding bound using an explicit alpha-spending schedule.
"""
import hashlib
import json
import math
import random
import unittest


def anytime_interval(errors, alpha=0.05):
    """Simultaneous coverage for all n >= 1 via union bound.

    At time n spend alpha_n = alpha / (n*(n+1)); sum alpha_n = alpha.
    Two-sided Hoeffding: P(|mean-p| >= radius) <= 2 exp(-2*n*r^2).
    Assumes independent bounded Bernoulli observations with common mean.
    NOT valid under clustered sampling, adaptively selected labels, or drift.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0,1)")
    n = len(errors)
    if not n:
        return (0.0, 1.0)
    if any(x not in (0, 1) for x in errors):
        raise ValueError("errors must be binary")
    radius = math.sqrt(math.log(2*n*(n+1)/alpha)/(2*n))
    mean = sum(errors)/n
    return (max(0.0, mean-radius), min(1.0, mean+radius))


def simulate(seed, trials=400, horizon=300, p=0.2):
    """Fresh independent streams, inspect every prefix, fixed compute budget."""
    rng = random.Random(seed)
    misses = 0
    fixed_misses = 0
    for _ in range(trials):
        observations = []
        ever_missed = False
        for _ in range(horizon):
            observations.append(int(rng.random() < p))
            low, high = anytime_interval(observations)
            ever_missed |= not (low <= p <= high)
        misses += ever_missed
        fixed_misses += not (low <= p <= high)
    receipt = {"seed": seed, "trials": trials, "horizon": horizon,
               "true_error": p, "anytime_misses": misses,
               "fixed_horizon_misses": fixed_misses,
               "method": "union_bound_hoeffding_v1",
               "assumptions": "iid_bernoulli_fully_observed"}
    digest = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return receipt, digest


class AnytimeAuditTests(unittest.TestCase):
    def test_empty_and_validation(self):
        self.assertEqual(anytime_interval([]), (0.0, 1.0))
        with self.assertRaises(ValueError):
            anytime_interval([2])
        with self.assertRaises(ValueError):
            anytime_interval([1], alpha=1.0)

    def test_monotone_precision_on_constant_mean(self):
        widths = [anytime_interval([0, 1]*k)[1] -
                  anytime_interval([0, 1]*k)[0] for k in (10, 100, 1000)]
        self.assertGreater(widths[0], widths[1])
        self.assertGreater(widths[1], widths[2])

    def test_independent_repeated_looks(self):
        receipt, digest = simulate(814, trials=100, horizon=120)
        self.assertLessEqual(receipt["anytime_misses"], 15)
        self.assertEqual((receipt, digest), simulate(814, trials=100, horizon=120))

    def test_counterexample_clustered_feedback(self):
        # Every group shares one latent label. Treating 200 duplicates as
        # independent produces an unjustifiably narrow interval.
        observations = [1]*200
        low, high = anytime_interval(observations)
        self.assertGreater(low, 0.5)
        # True p=0.2 remains possible with one independent cluster;
        # this failure is intentional, not an estimator guarantee.
        self.assertFalse(low <= 0.2 <= high)


if __name__ == "__main__":
    unittest.main()

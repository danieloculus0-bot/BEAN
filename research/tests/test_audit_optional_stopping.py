"""Synthetic negative control: repeated peeking invalidates fixed-time audit bounds.

No Core integration. Independent Bernoulli(0.5) outcomes, unlike potentially
correlated or selectively missing real feedback.
"""
import hashlib
import json
import math
import random
import unittest


def run(seed, horizon=100, alpha=0.05):
    if not isinstance(horizon, int) or horizon < 2 or not 0 < alpha < 1:
        raise ValueError("invalid horizon or alpha")
    rng = random.Random(seed)
    errors = [int(rng.random() < 0.5) for _ in range(horizon)]
    naive_first = anytime_first = None
    total = 0
    for n, error in enumerate(errors, 1):
        total += error
        if n < 10:
            continue
        deviation = abs(total/n - 0.5)
        fixed_radius = math.sqrt(math.log(2/alpha)/(2*n))
        anytime_radius = math.sqrt(math.log(2*horizon/alpha)/(2*n))
        if deviation > fixed_radius and naive_first is None:
            naive_first = n
        if deviation > anytime_radius and anytime_first is None:
            anytime_first = n
    receipt = {"seed":seed, "horizon":horizon, "alpha":alpha,
               "naive_cross":naive_first is not None,
               "anytime_cross":anytime_first is not None,
               "naive_first":naive_first, "anytime_first":anytime_first,
               "final_error":total/horizon, "observations":errors}
    receipt["sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return receipt


class OptionalStoppingAudit(unittest.TestCase):
    def test_repeated_peeking_inflates_false_alarm(self):
        rows = [run(seed) for seed in range(1000)]
        naive = sum(r["naive_cross"] for r in rows)
        anytime = sum(r["anytime_cross"] for r in rows)
        self.assertGreater(naive, anytime)
        self.assertLessEqual(anytime, 50)
        self.assertGreater(naive, 40)

    def test_anytime_cross_implies_naive_cross(self):
        for seed in range(200):
            r = run(seed)
            if r["anytime_cross"]:
                self.assertTrue(r["naive_cross"])

    def test_restart_and_tamper_receipt(self):
        original = run(42)
        restored = json.loads(json.dumps(original))
        self.assertEqual(restored, run(42))
        digest = restored.pop("sha256")
        self.assertEqual(digest, hashlib.sha256(json.dumps(restored, sort_keys=True).encode()).hexdigest())
        restored["observations"][0] ^= 1
        self.assertNotEqual(digest, hashlib.sha256(json.dumps(restored, sort_keys=True).encode()).hexdigest())

    def test_invalid_parameters(self):
        for horizon, alpha in ((1, .05), (100, 0), (100, 1), (100, -1)):
            with self.assertRaises(ValueError):
                run(0, horizon, alpha)


if __name__ == "__main__":
    unittest.main()

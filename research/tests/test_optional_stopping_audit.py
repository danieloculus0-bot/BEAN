"""Synthetic negative control: repeated Wilson peeking is not a confidence sequence.

Fixed-n 95% intervals do not retain simultaneous 95% coverage under optional
stopping. Research only: no BEAN inference or runtime changes.
"""
import hashlib
import json
import math
import random
import unittest


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z*z/n
    mid = (p + z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return (max(0.0, mid-half if k else 0.0),
            min(1.0, mid+half if k < n else 1.0))


def simulate(seed, trials=1500, max_n=120, truth=.5, min_n=10):
    """Independent Bernoulli trials; current label only revealed after draw."""
    rng = random.Random(seed)
    stopped = fixed_miss = 0
    stop_times = []
    for _ in range(trials):
        errors = 0
        first = None
        for n in range(1, max_n + 1):
            errors += rng.random() < truth
            if n >= min_n and first is None:
                lo, hi = wilson(errors, n)
                if not lo <= truth <= hi:
                    first = n
        fixed_miss += not (wilson(errors, max_n)[0] <= truth <=
                           wilson(errors, max_n)[1])
        if first is not None:
            stopped += 1
            stop_times.append(first)
    return {"seed": seed, "trials": trials, "max_n": max_n,
            "truth": truth, "min_n": min_n,
            "ever_missed": stopped, "fixed_missed": fixed_miss,
            "first_stop_times_sha256": hashlib.sha256(
                json.dumps(stop_times, separators=(',', ':')).encode()).hexdigest()}


class OptionalStoppingAuditControls(unittest.TestCase):
    def test_peeking_inflates_false_alarm_relative_to_fixed_horizon(self):
        for seed in (17, 29, 103):
            result = simulate(seed)
            self.assertGreater(result["ever_missed"], result["fixed_missed"] + 30)

    def test_stationary_control_and_replay(self):
        a = simulate(888, trials=200, truth=0.0)
        self.assertEqual(a, simulate(888, trials=200, truth=0.0))
        self.assertEqual(a["ever_missed"], 0)
        self.assertEqual(a["fixed_missed"], 0)

    def test_no_peeking_when_only_one_look_is_allowed(self):
        x = simulate(23, trials=200, min_n=120)
        self.assertEqual(x["ever_missed"], x["fixed_missed"])

    def test_no_audits_means_no_claim(self):
        self.assertEqual(wilson(0, 0), (0.0, 1.0))


if __name__ == "__main__":
    unittest.main()

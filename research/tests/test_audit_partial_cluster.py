"""Synthetic negative control: partially correlated feedback is not independent.

A cluster shares a latent Bernoulli error with probability rho; otherwise each
observation receives an independent Bernoulli draw. Marginal error is 0.5 and
within-cluster correlation is rho**2 (not rho). Known-null normal intervals
isolate pseudoreplication, not operational confidence calibration.
"""
import hashlib
import json
import math
import random
import unittest


def trial(seed, clusters=24, copies=10, shared_probability=0.7):
    if (type(clusters) is not int or clusters < 2 or type(copies) is not int
            or copies < 1 or not isinstance(shared_probability, (int, float))
            or not math.isfinite(shared_probability)
            or not 0 <= shared_probability <= 1):
        raise ValueError("invalid design")
    rng = random.Random(seed)
    outcomes = []
    for _ in range(clusters):
        latent = int(rng.random() < 0.5)
        outcomes.extend(latent if rng.random() < shared_probability else
                        int(rng.random() < 0.5) for _ in range(copies))
    n = len(outcomes)
    estimate = sum(outcomes) / n
    # Mixture covariance: two outcomes both choose the shared latent with p^2.
    icc = shared_probability ** 2
    design_effect = 1 + (copies - 1) * icc
    naive_radius = 1.96 * math.sqrt(0.25 / n)
    corrected_radius = naive_radius * math.sqrt(design_effect)
    receipt = dict(seed=seed, clusters=clusters, copies=copies,
                   shared_probability=shared_probability, assumed_icc=icc,
                   observations=outcomes, estimate=estimate,
                   naive_radius=naive_radius, corrected_radius=corrected_radius,
                   naive_miss=abs(estimate - 0.5) > naive_radius,
                   corrected_miss=abs(estimate - 0.5) > corrected_radius)
    receipt["sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return receipt


class PartialClusterDependence(unittest.TestCase):
    def test_paired_false_confidence(self):
        rows = [trial(s) for s in range(1500)]
        naive = sum(r["naive_miss"] for r in rows) / len(rows)
        corrected = sum(r["corrected_miss"] for r in rows) / len(rows)
        self.assertGreater(naive, 0.20)
        self.assertLess(corrected, 0.09)
        self.assertGreater(naive, corrected * 2)

    def test_independent_and_perfectly_shared_controls(self):
        for p in (0, 1):
            rows = [trial(s, shared_probability=p) for s in range(300)]
            self.assertLess(sum(r["corrected_miss"] for r in rows) / len(rows), 0.10)
            if p == 0:
                self.assertTrue(all(r["naive_radius"] == r["corrected_radius"] for r in rows))
            else:
                self.assertTrue(all(abs(r["corrected_radius"] -
                                        r["naive_radius"] * math.sqrt(10)) < 1e-12 for r in rows))

    def test_one_observation_per_cluster(self):
        for s in range(30):
            r = trial(s, copies=1)
            self.assertEqual(r["naive_radius"], r["corrected_radius"])

    def test_restart_and_tamper(self):
        r = trial(42)
        loaded = json.loads(json.dumps(r))
        digest = loaded.pop("sha256")
        self.assertEqual(digest, hashlib.sha256(json.dumps(loaded, sort_keys=True).encode()).hexdigest())
        loaded["observations"][0] ^= 1
        self.assertNotEqual(digest, hashlib.sha256(json.dumps(loaded, sort_keys=True).encode()).hexdigest())

    def test_invalid_design(self):
        for args in ((0, 1, .5), (2, 0, .5), (2, 3, -0.1), (2, 3, 1.1),
                     (2, 3, float("nan")), (True, 2, .5)):
            with self.assertRaises(ValueError):
                trial(1, *args)


if __name__ == "__main__":
    unittest.main()

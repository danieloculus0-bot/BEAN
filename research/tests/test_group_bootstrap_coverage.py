"""Synthetic negative control: row bootstrap undercovers with clustered errors.

No BEAN Core integration. Independent group-level latent outcomes create repeated
correlated observations; compare nominal 95% percentile intervals for population
mean using row resampling versus resampling the independent groups.
"""
import hashlib
import json
import random
import statistics
import unittest


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def trial(seed, groups=24, repeats=12, bootstrap=180):
    if groups < 2 or repeats < 1 or bootstrap < 10:
        raise ValueError("invalid independent-group design")
    rng = random.Random(seed)
    # Latent group-level errors are perfectly correlated across repeats.
    latent = [int(rng.random() < 0.5) for _ in range(groups)]
    rows = [v for v in latent for _ in range(repeats)]
    n = len(rows)
    row_estimates, group_estimates = [], []
    for _ in range(bootstrap):
        row_estimates.append(sum(rows[rng.randrange(n)] for _ in range(n)) / n)
        group_estimates.append(sum(latent[rng.randrange(groups)] for _ in range(groups)) / groups)
    return {
        "seed": seed, "groups": groups, "repeats": repeats,
        "row_ci": [percentile(row_estimates, 0.025), percentile(row_estimates, 0.975)],
        "group_ci": [percentile(group_estimates, 0.025), percentile(group_estimates, 0.975)],
        "observed": statistics.mean(latent), "population_mean": 0.5,
    }


def receipt(result):
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class GroupBootstrapCoverage(unittest.TestCase):
    def test_clustered_coverage(self):
        results = [trial(seed) for seed in range(120)]
        row_coverage = sum(r["row_ci"][0] <= 0.5 <= r["row_ci"][1] for r in results) / len(results)
        group_coverage = sum(r["group_ci"][0] <= 0.5 <= r["group_ci"][1] for r in results) / len(results)
        self.assertLess(row_coverage, 0.65)
        self.assertGreater(group_coverage, 0.85)
        self.assertGreater(group_coverage - row_coverage, 0.25)

    def test_single_observation_control(self):
        results = [trial(seed, repeats=1) for seed in range(50)]
        row = sum(r["row_ci"][0] <= 0.5 <= r["row_ci"][1] for r in results)
        group = sum(r["group_ci"][0] <= 0.5 <= r["group_ci"][1] for r in results)
        self.assertLessEqual(abs(row - group), 8)

    def test_restart_receipt_and_tamper(self):
        original = trial(71)
        recovered = json.loads(json.dumps(original))
        self.assertEqual(receipt(original), receipt(recovered))
        recovered["observed"] += 0.01
        self.assertNotEqual(receipt(original), receipt(recovered))

    def test_invalid_design(self):
        for args in ({"groups": 1}, {"repeats": 0}, {"bootstrap": 9}):
            with self.assertRaises(ValueError):
                trial(0, **args)


if __name__ == "__main__":
    unittest.main()

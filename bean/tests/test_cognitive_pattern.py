"""Numerical, leak, replay and exact-receipt tests for pattern mixture."""
import hashlib
import json
import math
import unittest
from experiments.cognitive_gauntlet.pattern_bayes import PatternMixtureBelief
from experiments.cognitive_gauntlet.pattern_benchmark import benchmark, ARMS, PARAMETERS
from experiments.cognitive_gauntlet.cognition import Evidence


class PatternTests(unittest.TestCase):
    def test_empty_state_and_invalid_parameters(self):
        model = PatternMixtureBelief(**PARAMETERS)
        self.assertEqual(model.prediction(), .5)
        self.assertEqual(model.pattern_posterior(), 0.)
        for args in ({"window": 0}, {"prior_alternating": float("nan")},
                     {"reliability_alpha": 0}, {"reliability_beta": -2}):
            with self.assertRaises(ValueError):
                PatternMixtureBelief(**args)

    def test_clean_alternating_observations(self):
        model = PatternMixtureBelief(**PARAMETERS)
        for i in range(15):
            model.observe(Evidence(str(i), f"s{i%5}", float(i%2), .65))
        self.assertGreater(model.pattern_posterior(), .8)
        self.assertGreater(model.prediction(), 0)
        self.assertLess(model.prediction(), 1)

    def test_stable_observations_dont_force_newest(self):
        model = PatternMixtureBelief(**PARAMETERS)
        for i in range(15):
            model.observe(Evidence(str(i), f"s{i%5}", 1., .65))
        self.assertLess(model.pattern_posterior(), .05)

    def test_duplicate_and_invalid_observation(self):
        model = PatternMixtureBelief(**PARAMETERS)
        model.observe(Evidence("one", "x", 1., .65))
        with self.assertRaises(ValueError):
            model.observe(Evidence("one", "x", 0., .65))
        with self.assertRaises(ValueError):
            model.observe(Evidence("bad", "x", float("nan"), .65))
        self.assertEqual(len(model.base.history), 1)

    def test_nonbinary_fallback(self):
        model = PatternMixtureBelief(**PARAMETERS)
        for i in range(11):
            model.observe(Evidence(str(i), "s", .7, .65))
        self.assertEqual(model.pattern_posterior(), 0.)
        self.assertEqual(model.prediction(), model.base.prediction())

    def test_disjoint_holdout_receipts_and_replay(self):
        settings = dict(heldout_start=20, heldout_seeds=2, rounds=9,
                        fresh_start=400, fresh_seeds=2, fresh_rounds=10)
        report = benchmark(**settings)
        self.assertEqual(report, benchmark(**settings))
        self.assertEqual(report["external_runtimes_executed"], [])
        unsigned = {k: v for k, v in report.items() if k != "receipt_sha256"}
        digest = hashlib.sha256(json.dumps(
            unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(report["receipt_sha256"], digest)
        self.assertEqual(len(report["heldout_original"]["cases"]), 54)
        self.assertEqual(len(report["additional_synthetic_families"]["cases"]), 160)
        for dataset, first in (("heldout_original", 20),
                               ("additional_synthetic_families", 400)):
            data = report[dataset]
            self.assertTrue(all(row["seed"] >= first for row in data["cases"]))
            for arm in ARMS:
                actual = sum(row["squared_error"][arm] for row in data["cases"])
                self.assertAlmostEqual(actual / len(data["cases"]),
                                       data["summary"]["all"]["mse"][arm])
            self.assertTrue(all(math.isfinite(row["predictions"]["pattern_mixture"])
                                for row in data["cases"]))


if __name__ == "__main__":
    unittest.main()

"""Holdout and provenance tests for volatility adaptation."""
import hashlib
import json
import unittest
from experiments.cognitive_gauntlet.adaptive import VolatilityAdaptiveBelief
from experiments.cognitive_gauntlet.adaptive_benchmark import benchmark, THRESHOLDS
from experiments.cognitive_gauntlet.cognition import Evidence


class AdaptiveTests(unittest.TestCase):
    def test_bounded_and_duplicate_evidence(self):
        model = VolatilityAdaptiveBelief()
        self.assertEqual(model.prediction(), 0.5)
        model.observe(Evidence("e1", "s", 1.0, 0.65))
        with self.assertRaises(ValueError):
            model.observe(Evidence("e1", "s", 0.0, 0.65))
        with self.assertRaises(ValueError):
            VolatilityAdaptiveBelief(threshold=float("nan"))

    def test_switches_when_observations_alternate(self):
        model = VolatilityAdaptiveBelief(threshold=0.65)
        for i in range(11):
            model.observe(Evidence(str(i), str(i % 5), float(i % 2), 0.65))
        self.assertEqual(model.mode(), "newest")
        self.assertEqual(model.prediction(), 0.0)

    def test_keeps_revising_when_observations_stable(self):
        model = VolatilityAdaptiveBelief()
        for i in range(11):
            model.observe(Evidence(str(i), str(i % 5), 1.0, 0.65))
        self.assertEqual(model.mode(), "revision")
        self.assertLess(model.prediction(), 1.0)

    def test_holdout_disjoint_deterministic_and_digest(self):
        a = benchmark(seeds=6, training_seeds=2, rounds=9)
        self.assertEqual(a, benchmark(seeds=6, training_seeds=2, rounds=9))
        self.assertIn(a["selected_threshold"], THRESHOLDS)
        self.assertEqual(len(a["training"]["cases"]), 54)
        self.assertEqual(len(a["heldout"]["cases"]), 108)
        self.assertTrue(all(x["seed"] < 2 for x in a["training"]["cases"]))
        self.assertTrue(all(x["seed"] >= 2 for x in a["heldout"]["cases"]))
        self.assertEqual(a["external_runtimes_executed"], [])
        raw = {k: v for k, v in a.items() if k != "receipt_sha256"}
        serial = json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(a["receipt_sha256"], hashlib.sha256(serial.encode()).hexdigest())

    def test_all_losses_reconcile(self):
        a = benchmark(seeds=7, training_seeds=3, rounds=12)
        for split in ("training", "heldout"):
            rows = a[split]["cases"]
            for scenario, group in a[split]["by_scenario"].items():
                part = [r for r in rows if r["scenario"] == scenario]
                self.assertEqual(group["n"], len(part))
                for arm, mse in group["mse"].items():
                    self.assertAlmostEqual(mse, sum(r["squared_error"][arm] for r in part) / len(part))


if __name__ == "__main__":
    unittest.main()

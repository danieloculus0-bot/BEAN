"""Regression checks for independent stress scenarios."""
import hashlib
import json
import unittest
from experiments.cognitive_gauntlet.stress import stress, REGIMES


class StressTests(unittest.TestCase):
    def test_reproducible_unseen_conditions(self):
        a = stress(first_seed=80, seeds=2, rounds=10)
        self.assertEqual(a, stress(first_seed=80, seeds=2, rounds=10))
        self.assertEqual(len(a["cases"]), 80)
        self.assertEqual(set(a["summary"]), set(REGIMES))
        self.assertEqual(a["external_runtimes_executed"], [])

    def test_all_losses_reconcile(self):
        report = stress(first_seed=80, seeds=3, rounds=12)
        for regime, summary in report["summary"].items():
            rows = [c for c in report["cases"] if c["regime"] == regime]
            for arm, score in summary.items():
                self.assertAlmostEqual(score, sum(c["errors"][arm] for c in rows) / len(rows))

    def test_digest_integrity(self):
        report = stress(first_seed=80, seeds=2, rounds=10)
        original = {k: v for k, v in report.items() if k != "receipt_sha256"}
        canonical = json.dumps(original, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.assertEqual(report["receipt_sha256"], hashlib.sha256(canonical.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()

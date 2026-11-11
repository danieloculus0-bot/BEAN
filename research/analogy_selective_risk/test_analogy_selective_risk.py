"""Synthetic negative control for cross-domain analogy confidence under shift.

No BEAN runtime integration or validated analogy transfer is claimed.
Run: python -m unittest -v test_analogy_selective_risk.py
"""
import random
import unittest

SEED = 20261105


def cases(seed, n, shifted=False):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        # Lexical overlap is deliberately misleading on a shifted domain.
        score = rng.uniform(0.50, 1.0)
        success = rng.random() < (0.15 if shifted else score)
        rows.append((score, int(success)))
    return rows


def selective(rows, threshold):
    selected = [ok for score, ok in rows if score >= threshold]
    return {"coverage": len(selected) / len(rows),
            "error": (1 - sum(selected) / len(selected)) if selected else None,
            "n": len(selected)}


class SelectiveRiskControl(unittest.TestCase):
    def test_frozen_threshold_fails_under_shift(self):
        train = cases(SEED, 1000)
        # Select on training only. No held-out labels used to tune threshold.
        thresholds = [0.50, 0.60, 0.70, 0.80, 0.90]
        eligible = [t for t in thresholds if selective(train, t)["error"] <= 0.20]
        self.assertTrue(eligible)
        chosen = min(eligible)
        held = selective(cases(SEED + 1, 1000), chosen)
        shift = selective(cases(SEED + 2, 1000, shifted=True), chosen)
        self.assertGreater(held["n"], 100)
        self.assertGreater(shift["n"], 100)
        self.assertGreater(shift["error"], held["error"] + 0.45)

    def test_replay_is_deterministic(self):
        self.assertEqual(cases(SEED, 200), cases(SEED, 200))

    def test_no_selection_is_not_zero_error(self):
        self.assertIsNone(selective(cases(SEED, 50), 1.01)["error"])

    def test_negative_evidence_preserved(self):
        shifted = cases(SEED + 2, 1000, shifted=True)
        self.assertGreater(sum(1 for _, ok in shifted if not ok), 700)


if __name__ == "__main__":
    unittest.main()

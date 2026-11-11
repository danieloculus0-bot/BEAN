"""Synthetic intervention-selected feature, tested on unseen proxy reversal.

Research-only; no BEAN Core runtime change or learned causal discovery.
Run: python -m unittest discover -s research/causal_probe -p 'test_*.py'
"""
import random
import unittest


def cohort(seed, n, regime):
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        x = rng.randrange(2)
        if regime == "observational":
            proxy = x
        elif regime == "intervention":
            proxy = rng.randrange(2)
        elif regime == "reversed":
            proxy = 1 - x
        else:
            raise ValueError(regime)
        rows.append((x, proxy, x))
    return rows


def accuracy(rows, feature):
    return sum(row[feature] == row[2] for row in rows) / len(rows)


def select(validation):
    """Return unresolved on ties; do not prefer the causal feature by fiat."""
    scores = (accuracy(validation, 0), accuracy(validation, 1))
    if scores[0] == scores[1]:
        return None
    return 0 if scores[0] > scores[1] else 1


def run(seed=20261104, n=200):
    training = cohort(seed, n, "observational")
    validation = cohort(seed + 1, n, "intervention")
    heldout = cohort(seed + 2, n, "reversed")
    chosen = select(validation)
    return {
        "seed": seed, "n": n,
        "training_accuracy": [accuracy(training, f) for f in (0, 1)],
        "validation_accuracy": [accuracy(validation, f) for f in (0, 1)],
        "selected_feature": chosen,
        "heldout_accuracy": None if chosen is None else accuracy(heldout, chosen),
        "proxy_heldout_accuracy": accuracy(heldout, 1),
        "heldout_regime": "reversed",
    }


class TestSelection(unittest.TestCase):
    def test_observational_tie_cannot_identify_cause(self):
        self.assertIsNone(select(cohort(1, 200, "observational")))

    def test_intervention_selects_invariant_feature(self):
        self.assertEqual(select(cohort(2, 200, "intervention")), 0)

    def test_fresh_reversed_proxy_heldout(self):
        result = run()
        self.assertEqual(result["selected_feature"], 0)
        self.assertEqual(result["heldout_accuracy"], 1.0)
        self.assertEqual(result["proxy_heldout_accuracy"], 0.0)

    def test_reproducible(self):
        self.assertEqual(run(17), run(17))

    def test_no_unseen_regime_leak_into_selection(self):
        validation = cohort(4, 200, "intervention")
        before = select(validation)
        _ = cohort(5, 200, "reversed")
        self.assertEqual(before, select(validation))

    def test_invalid_regime_rejected(self):
        with self.assertRaises(ValueError):
            cohort(1, 1, "unknown")


if __name__ == "__main__":
    unittest.main()

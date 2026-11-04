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
    """Select only with one-sided exact paired evidence, otherwise abstain.

    Discordant rows are the independent Bernoulli trials under a tied
    predictor null. This is a research diagnostic, not causal identification.
    """
    if not validation:
        return None
    wins = sum(row[0] == row[2] and row[1] != row[2] for row in validation)
    losses = sum(row[1] == row[2] and row[0] != row[2] for row in validation)
    n = wins + losses
    if not n:
        return None
    from math import comb
    tail = sum(comb(n, k) for k in range(max(wins, losses), n + 1)) / (2 ** n)
    if tail > 0.05:
        return None
    return 0 if wins > losses else 1


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

    def test_single_discordance_is_not_evidence(self):
        self.assertIsNone(select([(1, 0, 1)]))

    def test_empty_validation_abstains(self):
        self.assertIsNone(select([]))

    def test_five_discordances_are_significant(self):
        self.assertEqual(select([(1, 0, 1)] * 5), 0)

    def test_four_discordances_are_insufficient(self):
        self.assertIsNone(select([(1, 0, 1)] * 4))

    def test_opposite_direction_and_negative_evidence(self):
        self.assertEqual(select([(0, 1, 1)] * 6), 1)
        self.assertIsNone(select([(1, 0, 1)] * 6 + [(0, 1, 1)] * 6))

    def test_invalid_regime_rejected(self):
        with self.assertRaises(ValueError):
            cohort(1, 1, "unknown")


if __name__ == "__main__":
    unittest.main()

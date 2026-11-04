"""Synthetic causal-transfer falsification probe (stdlib only).

Research-only: this does not alter BEAN Core or claim causal discovery.
Run: python -m unittest discover -s research/causal_probe -p 'test_*.py'
"""
import random
import unittest


def generate(seed, n=200, intervention=False):
    """A is a spurious proxy for environment E; Y is caused by X.

    In observational data A and X coincide. Under intervention, A is
    independently randomized, so proxy memorization fails.
    """
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        x = rng.randrange(2)
        a = rng.randrange(2) if intervention else x
        y = x
        rows.append((x, a, y))
    return rows


def score(rows, predictor):
    return sum(int(predictor(x, a) == y) for x, a, y in rows) / len(rows)


def evaluate(seed=20261104, n=200):
    train = generate(seed, n, intervention=False)
    heldout = generate(seed + 1, n, intervention=True)
    causal = lambda x, a: x
    proxy = lambda x, a: a
    return {
        "seed": seed,
        "n": n,
        "observational": {
            "causal": score(train, causal),
            "proxy": score(train, proxy),
        },
        "intervention": {
            "causal": score(heldout, causal),
            "proxy": score(heldout, proxy),
        },
    }


class TestCausalIntervention(unittest.TestCase):
    def test_observational_equivalence(self):
        result = evaluate()
        self.assertEqual(result["observational"], {"causal": 1.0, "proxy": 1.0})

    def test_intervention_breaks_proxy(self):
        result = evaluate()
        self.assertEqual(result["intervention"]["causal"], 1.0)
        self.assertLess(result["intervention"]["proxy"], 0.65)

    def test_reproducible_seed(self):
        self.assertEqual(evaluate(42), evaluate(42))

    def test_distinct_heldout(self):
        self.assertNotEqual(generate(42, 100), generate(43, 100, True))

    def test_no_test_data_in_training(self):
        # Separate RNG seeds and intervention regimes, not a guarantee of
        # independent provenance in external datasets.
        train = generate(42, 200, False)
        test = generate(43, 200, True)
        self.assertTrue(all(x == a for x, a, _ in train))
        self.assertTrue(any(x != a for x, a, _ in test))


if __name__ == "__main__":
    unittest.main()

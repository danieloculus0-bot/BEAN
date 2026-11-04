"""Research-only sequential testing guard for repeated looks at paired evidence.

Bonferroni across features alone does not correct repeated peeking at the
same feature. Predeclare the maximum number of looks; never expand it after
observing outcomes. This is not an anytime-valid test.
"""
from math import comb, isfinite
import unittest


def paired_sign_p(wins: int, losses: int) -> float:
    """One-sided exact sign-test tail; ties excluded, no asymptotics."""
    if any(type(v) is not int or v < 0 for v in (wins, losses)):
        raise ValueError("counts must be nonnegative integers")
    n = wins + losses
    if not n:
        return 1.0
    return sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n)


def sequential_decision(wins: int, losses: int, *, look: int,
                        max_looks: int, features: int, alpha: float = 0.05) -> dict:
    """Conservative familywise alpha allocation across features and looks."""
    if any(type(v) is not int or v < 1 for v in (look, max_looks, features)):
        raise ValueError("look, max_looks and features must be positive integers")
    if look > max_looks:
        raise ValueError("unregistered extra look")
    if not isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one")
    p = paired_sign_p(wins, losses)
    threshold = alpha / (features * max_looks)
    return {"p": p, "threshold": threshold,
            "supported": wins > losses and p <= threshold,
            "look": look, "max_looks": max_looks, "features": features}


class SequentialGuardTests(unittest.TestCase):
    def test_single_look(self):
        self.assertTrue(sequential_decision(5, 0, look=1, max_looks=1, features=1)["supported"])

    def test_repeated_looks_prevent_premature_claim(self):
        self.assertFalse(sequential_decision(5, 0, look=1, max_looks=4, features=1)["supported"])

    def test_more_independent_evidence_can_pass(self):
        self.assertTrue(sequential_decision(8, 0, look=4, max_looks=4, features=1)["supported"])

    def test_negative_evidence_is_not_erased(self):
        self.assertFalse(sequential_decision(4, 4, look=2, max_looks=4, features=1)["supported"])

    def test_unregistered_peek_rejected(self):
        with self.assertRaises(ValueError):
            sequential_decision(10, 0, look=5, max_looks=4, features=1)

    def test_feature_search_adjusted(self):
        self.assertFalse(sequential_decision(6, 0, look=1, max_looks=2, features=4)["supported"])

    def test_invalid_input(self):
        for args in [(True, 0), (-1, 0), (1.0, 0)]:
            with self.assertRaises(ValueError):
                paired_sign_p(*args)


if __name__ == "__main__":
    unittest.main()

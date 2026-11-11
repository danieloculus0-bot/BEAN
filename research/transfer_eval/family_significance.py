"""Exact family-level sign test for paired transfer experiments.

Research-only diagnostic. Family independence and preregistration anchor
must be verified externally; p-values do not prove transfer or AGI.
"""
from math import comb


def family_sign_test(score):
    """One-sided exact sign test of family wins vs losses, excluding ties.

    The conservative family score treats any within-family regression as a loss.
    Under the null of equal win/loss probability across independent families,
    P(X >= wins | n=non-tied families) is calculated without asymptotics.
    """
    if not isinstance(score, dict) or score.get("valid") is not True:
        return {"valid": False, "reason": "invalid_or_incomplete_family_audit"}
    wins, losses, ties = (score.get(k) for k in
                           ("family_wins", "family_losses", "family_ties"))
    if any(type(v) is not int or v < 0 for v in (wins, losses, ties)):
        return {"valid": False, "reason": "invalid_family_counts"}
    if wins + losses + ties != score.get("family_count"):
        return {"valid": False, "reason": "inconsistent_family_counts"}
    n = wins + losses
    if n == 0:
        return {"valid": True, "nontied_families": 0,
                "one_sided_p": 1.0, "evidence_of_gain_at_0_05": False,
                "claim": "descriptive_only_independence_unverified"}
    p = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
    return {"valid": True, "nontied_families": n,
            "one_sided_p": p, "evidence_of_gain_at_0_05": p < 0.05,
            "claim": "conditional_sign_test_independence_unverified"}


if __name__ == "__main__":
    import unittest

    class SyntheticControls(unittest.TestCase):
        def score(self, w, l, t=0):
            return {"valid": True, "family_wins": w, "family_losses": l,
                    "family_ties": t, "family_count": w+l+t}

        def test_one_win_not_significant(self):
            self.assertEqual(family_sign_test(self.score(1, 0))["one_sided_p"], 0.5)

        def test_six_independent_wins(self):
            r = family_sign_test(self.score(6, 0))
            self.assertEqual(r["one_sided_p"], 1/64)
            self.assertTrue(r["evidence_of_gain_at_0_05"])

        def test_losses_preserved(self):
            self.assertEqual(family_sign_test(self.score(3, 2))["one_sided_p"], 0.5)

        def test_ties_excluded(self):
            self.assertEqual(family_sign_test(self.score(1, 1, 8))["one_sided_p"], 0.75)

        def test_no_evidence(self):
            self.assertFalse(family_sign_test(self.score(0, 0, 5))["evidence_of_gain_at_0_05"])

        def test_invalid_and_inconsistent(self):
            self.assertFalse(family_sign_test({"valid": False})["valid"])
            s = self.score(1, 0)
            s["family_count"] = 3
            self.assertFalse(family_sign_test(s)["valid"])

    unittest.main()

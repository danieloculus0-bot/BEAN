"""Synthetic negative controls for family-clustered transfer scoring."""
import unittest
from research.transfer_eval.preregistration import canonical_digest
from research.transfer_eval.family_score import family_paired_score


class FamilyScoreTests(unittest.TestCase):
    def plan(self):
        return {"baseline_sha": "baseline", "candidate_sha": "candidate",
                "seed": 19, "budget": {"calls": 3},
                "cases": [
                    {"case_id": "a1", "family_id": "A", "target_domain": "x", "split": "heldout"},
                    {"case_id": "a2", "family_id": "A", "target_domain": "x", "split": "heldout"},
                    {"case_id": "a3", "family_id": "A", "target_domain": "x", "split": "heldout"},
                    {"case_id": "b1", "family_id": "B", "target_domain": "y", "split": "ood"}]}

    def test_correlated_wins_do_not_outvote_independent_loss(self):
        p = self.plan()
        outcomes = [{"case_id": k, "baseline": False, "candidate": True}
                    for k in ("a1", "a2", "a3")]
        outcomes.append({"case_id": "b1", "baseline": True, "candidate": False})
        result = family_paired_score(p, canonical_digest(p), outcomes)
        self.assertEqual(result["case_audit"]["paired_net_gain"], 2)
        self.assertEqual(result["family_net_gain"], 0)
        self.assertEqual((result["family_wins"], result["family_losses"]), (1, 1))

    def test_within_family_regression_is_not_hidden(self):
        p = self.plan()
        outcomes = [{"case_id": "a1", "baseline": False, "candidate": True},
                    {"case_id": "a2", "baseline": False, "candidate": True},
                    {"case_id": "a3", "baseline": True, "candidate": False},
                    {"case_id": "b1", "baseline": True, "candidate": True}]
        result = family_paired_score(p, canonical_digest(p), outcomes)
        self.assertEqual(result["family_net_gain"], -1)

    def test_missing_case_cannot_generate_gain(self):
        p = self.plan()
        result = family_paired_score(p, canonical_digest(p),
                                     [{"case_id": "a1", "baseline": False, "candidate": True}])
        self.assertFalse(result["valid"])
        self.assertIsNone(result["family_net_gain"])

    def test_tampered_anchor_rejected(self):
        p = self.plan()
        result = family_paired_score(p, "bad", [])
        self.assertFalse(result["valid"])
        self.assertIsNone(result["family_net_gain"])


if __name__ == "__main__":
    unittest.main()

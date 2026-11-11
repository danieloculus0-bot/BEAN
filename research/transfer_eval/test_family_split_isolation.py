"""Synthetic regression controls for train/evaluation dependency-family leakage."""
import unittest
from research.transfer_eval.preregistration import canonical_digest, audit_preregistration


def plan():
    return {"baseline_sha": "baseline-r1", "candidate_sha": "candidate-r2",
            "seed": 11, "budget": {"calls": 2},
            "cases": [
                {"case_id": "train-1", "family_id": "family-A", "target_domain": "logic", "split": "train"},
                {"case_id": "held-1", "family_id": "family-B", "target_domain": "navigation", "split": "heldout"},
                {"case_id": "ood-1", "family_id": "family-C", "target_domain": "planning", "split": "ood"}]}


class FamilyIsolationTests(unittest.TestCase):
    def test_disjoint_family_plan_remains_valid(self):
        p = plan()
        digest = canonical_digest(p)
        result = audit_preregistration(p, digest, [
            {"case_id": "held-1", "baseline": True, "candidate": False},
            {"case_id": "ood-1", "baseline": False, "candidate": False}])
        self.assertTrue(result["valid"])
        self.assertEqual(result["paired_losses"], 1)
        self.assertEqual(result["paired_net_gain"], -1)

    def test_train_to_heldout_overlap_rejected(self):
        p = plan()
        p["cases"][1]["family_id"] = "family-A"
        with self.assertRaisesRegex(ValueError, "family leakage"):
            canonical_digest(p)

    def test_train_to_ood_overlap_rejected(self):
        p = plan()
        p["cases"][2]["family_id"] = "family-A"
        with self.assertRaisesRegex(ValueError, "family leakage"):
            canonical_digest(p)

    def test_distinct_eval_cases_same_family_not_misrepresented_as_train_leak(self):
        p = plan()
        p["cases"][2]["family_id"] = "family-B"
        self.assertEqual(len(canonical_digest(p)), 64)


if __name__ == "__main__":
    unittest.main()

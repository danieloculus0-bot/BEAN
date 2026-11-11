"""Synthetic controls for vacuous frozen evaluation plans."""
import unittest
from research.transfer_eval.preregistration import canonical_digest, audit_preregistration


def make_plan(split):
    return {
        "baseline_sha": "a" * 40, "candidate_sha": "b" * 40,
        "seed": 17, "budget": {"inference_tokens": 100},
        "cases": [{"case_id": "case-1", "family_id": "family-1",
                   "target_domain": "synthetic-logic", "split": split}],
    }


class TestNonvacuousEvaluation(unittest.TestCase):
    def test_training_only_plan_cannot_pass_with_empty_outcomes(self):
        plan = make_plan("train")
        result = audit_preregistration(plan, canonical_digest(plan), [])
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "no_heldout_or_ood_cases")

    def test_training_only_plan_cannot_pass_with_train_outcome(self):
        plan = make_plan("train")
        result = audit_preregistration(plan, canonical_digest(plan),
                                       [{"case_id": "case-1", "baseline": False, "candidate": True}])
        self.assertFalse(result["valid"])

    def test_heldout_plan_requires_observed_case(self):
        plan = make_plan("heldout")
        result = audit_preregistration(plan, canonical_digest(plan), [])
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "missing_or_extra_cases")

    def test_ood_plan_accepts_complete_negative_result(self):
        plan = make_plan("ood")
        result = audit_preregistration(plan, canonical_digest(plan),
                                       [{"case_id": "case-1", "baseline": True, "candidate": False}])
        self.assertTrue(result["valid"])
        self.assertEqual(result["observed_cases"], 1)


if __name__ == "__main__":
    unittest.main()

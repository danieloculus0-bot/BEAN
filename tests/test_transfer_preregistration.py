"""Synthetic negative controls for preregistration integrity."""
import unittest
from research.transfer_eval.preregistration import canonical_digest, audit_preregistration


def plan():
    return {"baseline_sha": "a" * 40, "candidate_sha": "b" * 40,
            "seed": 7, "budget": {"inference_tokens": 200},
            "cases": [{"case_id": "h1", "family_id": "f1", "target_domain": "logic",
                       "split": "heldout"},
                      {"case_id": "o1", "family_id": "f2", "target_domain": "control",
                       "split": "ood"},
                      {"case_id": "t1", "family_id": "f3", "target_domain": "logic",
                       "split": "train"}]}


def outcomes():
    return [{"case_id": "h1", "baseline": False, "candidate": True},
            {"case_id": "o1", "baseline": True, "candidate": False}]


class TestPreregistration(unittest.TestCase):
    def test_complete_frozen_eval(self):
        p = plan()
        self.assertTrue(audit_preregistration(p, canonical_digest(p), outcomes())["valid"])

    def test_changed_seed_fails(self):
        p = plan()
        digest = canonical_digest(p)
        p["seed"] = 8
        self.assertFalse(audit_preregistration(p, digest, outcomes())["valid"])

    def test_missing_failure_fails(self):
        p = plan()
        self.assertFalse(audit_preregistration(p, canonical_digest(p), outcomes()[:1])["valid"])

    def test_train_case_in_eval_fails(self):
        p = plan()
        observed = outcomes() + [{"case_id": "t1", "baseline": True, "candidate": True}]
        self.assertFalse(audit_preregistration(p, canonical_digest(p), observed)["valid"])

    def test_duplicate_case_rejected(self):
        p = plan()
        p["cases"].append(dict(p["cases"][0]))
        with self.assertRaises(ValueError):
            canonical_digest(p)

    def test_duplicate_outcome_rejected(self):
        p = plan()
        with self.assertRaises(ValueError):
            audit_preregistration(p, canonical_digest(p), outcomes() + outcomes()[:1])


if __name__ == "__main__":
    unittest.main()

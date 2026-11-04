"""Synthetic negative controls for ambiguous preregistration labels."""
import unittest
from research.transfer_eval.preregistration import canonical_digest, audit_preregistration


def plan():
    return {
        "baseline_sha": "base123", "candidate_sha": "candidate456",
        "seed": 7, "budget": {"tokens": 100},
        "cases": [
            {"case_id": "case-1", "family_id": "family-1",
             "target_domain": "domain-a", "split": "ood"},
        ],
    }


class CanonicalLabelTests(unittest.TestCase):
    def test_case_id_whitespace_rejected(self):
        p = plan()
        p["cases"][0]["case_id"] = " case-1"
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            canonical_digest(p)

    def test_family_whitespace_rejected(self):
        p = plan()
        p["cases"][0]["family_id"] = "family-1 "
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            canonical_digest(p)

    def test_domain_and_split_whitespace_rejected(self):
        for key in ("target_domain", "split"):
            with self.subTest(key=key):
                p = plan()
                p["cases"][0][key] += " "
                with self.assertRaisesRegex(ValueError, "noncanonical"):
                    canonical_digest(p)

    def test_negative_outcome_preserved(self):
        p = plan()
        result = audit_preregistration(
            p, canonical_digest(p),
            [{"case_id": "case-1", "baseline": True, "candidate": False}],
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["paired_losses"], 1)
        self.assertEqual(result["paired_net_gain"], -1)


if __name__ == "__main__":
    unittest.main()

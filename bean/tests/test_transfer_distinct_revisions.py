"""Synthetic controls for frozen evaluation revision identity."""
import unittest
from research.transfer_eval.preregistration import canonical_digest, audit_preregistration


def plan(baseline="base123", candidate="candidate456"):
    return {"baseline_sha": baseline, "candidate_sha": candidate,
            "seed": 7, "budget": {"tokens": 100},
            "cases": [{"case_id": "novel-1", "family_id": "unseen-family",
                       "target_domain": "synthetic-domain", "split": "ood"}]}


class DistinctRevisionTests(unittest.TestCase):
    def test_identical_revisions_rejected(self):
        with self.assertRaisesRegex(ValueError, "identical"):
            canonical_digest(plan("same", "same"))

    def test_whitespace_variant_rejected(self):
        with self.assertRaisesRegex(ValueError, "identical"):
            canonical_digest(plan(" same ", "same"))

    def test_distinct_revisions_still_allow_negative_result(self):
        p = plan()
        result = audit_preregistration(p, canonical_digest(p),
                                       [{"case_id": "novel-1", "baseline": True,
                                         "candidate": False}])
        self.assertTrue(result["valid"])
        self.assertEqual(result["paired_losses"], 1)
        self.assertEqual(result["paired_net_gain"], -1)


if __name__ == "__main__":
    unittest.main()

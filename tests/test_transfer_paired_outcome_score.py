"""Synthetic paired outcome controls; integrity is not proof of transfer."""
import unittest
from research.transfer_eval.preregistration import canonical_digest, audit_preregistration


def plan():
    return {"baseline_sha": "a" * 40, "candidate_sha": "b" * 40,
            "seed": 19, "budget": {"inference_tokens": 100},
            "cases": [{"case_id": f"c{i}", "family_id": f"f{i}",
                       "target_domain": "synthetic", "split": "ood"} for i in range(4)]}


class TestPairedOutcomeScore(unittest.TestCase):
    def test_matched_wins_losses_ties_are_preserved(self):
        p = plan()
        outcomes = [
            {"case_id": "c0", "baseline": False, "candidate": True},
            {"case_id": "c1", "baseline": True, "candidate": False},
            {"case_id": "c2", "baseline": False, "candidate": False},
            {"case_id": "c3", "baseline": True, "candidate": True},
        ]
        result = audit_preregistration(p, canonical_digest(p), outcomes)
        self.assertTrue(result["valid"])
        self.assertEqual((result["paired_wins"], result["paired_losses"],
                          result["paired_ties"], result["paired_net_gain"]), (1, 1, 2, 0))

    def test_missing_case_is_invalid_despite_positive_net(self):
        p = plan()
        result = audit_preregistration(p, canonical_digest(p),
            [{"case_id": "c0", "baseline": False, "candidate": True}])
        self.assertFalse(result["valid"])
        self.assertEqual(result["paired_net_gain"], 1)

    def test_negative_result_is_not_dropped(self):
        p = plan()
        outcomes = [{"case_id": f"c{i}", "baseline": True, "candidate": False}
                    for i in range(4)]
        result = audit_preregistration(p, canonical_digest(p), outcomes)
        self.assertTrue(result["valid"])
        self.assertEqual(result["paired_losses"], 4)
        self.assertEqual(result["paired_net_gain"], -4)


if __name__ == "__main__":
    unittest.main()

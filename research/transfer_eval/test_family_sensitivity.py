"""Synthetic sensitivity controls, not BEAN learning measurements."""
import unittest
from research.transfer_eval.family_sensitivity import leave_one_family_out


def row(case, family, baseline, candidate):
    return {"case_id": case, "family_id": family,
            "baseline_correct": baseline, "candidate_correct": candidate}


class SensitivityTests(unittest.TestCase):
    def test_single_winning_family_does_not_survive_deletion(self):
        rows = [row(f"p{i}", "paraphrase", False, True) for i in range(20)]
        rows += [row("regression", "other", True, False)]
        result = leave_one_family_out(rows)
        self.assertEqual(result["full"]["case_wins"], 20)
        self.assertFalse(result["robust_majority"])
        self.assertEqual(result["deletions"]["paraphrase"]["family_losses"], 1)

    def test_three_distinct_winning_families_survive_deletion(self):
        rows = [row(str(i), str(i), False, True) for i in range(3)]
        self.assertTrue(leave_one_family_out(iter(rows))["robust_majority"])

    def test_one_family_is_inconclusive(self):
        result = leave_one_family_out([row("x", "same", False, True)])
        self.assertFalse(result["robust_majority"])
        self.assertEqual(result["reason"], "fewer_than_two_dependency_families")

    def test_invalid_case_still_rejected(self):
        with self.assertRaises(ValueError):
            leave_one_family_out([row("x", "a", False, True),
                                  row("x", "b", False, True)])


if __name__ == "__main__":
    unittest.main()

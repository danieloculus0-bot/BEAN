"""Synthetic negative controls for dependency-aware transfer accounting."""
import unittest
from research.transfer_eval.paired_families import score_pairs


class PairedFamiliesTests(unittest.TestCase):
    def test_correlated_cases_not_counted_as_independent_families(self):
        rows = [
            {"case_id": f"rephrase-{i}", "family_id": "same-causal-task",
             "baseline_correct": False, "candidate_correct": True}
            for i in range(20)
        ]
        result = score_pairs(rows)
        self.assertEqual(result["case_wins"], 20)
        self.assertEqual(result["family_wins"], 1)
        self.assertEqual(result["dependency_families"], 1)

    def test_regression_and_tie_preserved(self):
        rows = [
            {"case_id": "a", "family_id": "A", "baseline_correct": True, "candidate_correct": False},
            {"case_id": "b", "family_id": "B", "baseline_correct": False, "candidate_correct": True},
            {"case_id": "c", "family_id": "C", "baseline_correct": True, "candidate_correct": True},
        ]
        result = score_pairs(rows)
        self.assertEqual((result["family_wins"], result["family_losses"], result["family_ties"]), (1, 1, 1))

    def test_reject_duplicate_or_unscored(self):
        a = {"case_id": "a", "family_id": "A", "baseline_correct": True, "candidate_correct": False}
        with self.assertRaises(ValueError):
            score_pairs([a, a])
        with self.assertRaises(ValueError):
            score_pairs([{**a, "candidate_correct": None}])
        with self.assertRaises(ValueError):
            score_pairs([])


if __name__ == "__main__":
    unittest.main()

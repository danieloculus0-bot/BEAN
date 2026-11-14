"""Strong-control reporting must not omit the grammar-matched comparator."""
import unittest

from bean.evaluation.github_digital_cycle import FAMILIES
from scripts.simulate_restored_core import coverage_metrics


class StrongControlCoverageTests(unittest.TestCase):
    def test_strong_control_tie_is_visible(self):
        families = {
            family: {
                "correct": {
                    "candidate": 48, "grammar_matched": 48,
                    "passive": 32, "memory_ablated": 32,
                    "shuffled": 0, "always_zero": 0,
                },
                "abstentions": {
                    "candidate": 0, "grammar_matched": 0,
                    "passive": 0, "memory_ablated": 0,
                    "shuffled": 48,
                },
            }
            for family in FAMILIES
        }
        metrics = coverage_metrics(families)
        self.assertEqual(metrics["candidate"]["correct"], 144)
        self.assertEqual(metrics["grammar_matched"]["correct"], 144)
        self.assertEqual(metrics["grammar_matched"]["coverage"], 1.0)
        self.assertEqual(metrics["passive"]["correct"], 96)

    def test_legacy_missing_strong_control_is_unknown_not_zero(self):
        families = {
            family: {
                "correct": {
                    "candidate": 48, "passive": 48,
                    "memory_ablated": 0, "shuffled": 0, "always_zero": 0,
                },
                "abstentions": {
                    "candidate": 0, "passive": 0,
                    "memory_ablated": 48, "shuffled": 48,
                },
            }
            for family in FAMILIES
        }
        metrics = coverage_metrics(families)
        self.assertEqual(metrics["grammar_matched"]["status"], "Unknown")
        self.assertIsNone(metrics["grammar_matched"]["correct"])
        self.assertIsNone(metrics["grammar_matched"]["all_case_accuracy"])


if __name__ == "__main__":
    unittest.main()

"""Falsification control: decision scoring does not verify retrieved evidence exists.

This intentionally preserves a negative result. It is not a semantic-retrieval
improvement and does not change BEAN's memory or reasoning runtime.
"""
import unittest

from bean.tests.test_analogy_selective_risk_control import score_decisions


class CandidateUniverseNegativeControl(unittest.TestCase):
    def test_unavailable_evidence_id_can_be_scored_correct(self):
        # Synthetic, independently specified candidate inventory and labels.
        # The gold label refers to a precedent absent from the inventory.
        available = {"task-1": {"receipt-available"}}
        gold = {"task-1": "receipt-missing"}
        predicted = {"task-1": "receipt-missing"}
        self.assertNotIn(gold["task-1"], available["task-1"])
        # Current evaluator returns 1.0 despite impossible provenance.
        result = score_decisions(gold, predicted)
        self.assertEqual(result["decision_accuracy"], 1.0)
        self.assertEqual(result["coverage"], 1.0)

    def test_abstention_control_with_missing_gold(self):
        available = {"task-1": {"receipt-available"}}
        gold = {"task-1": None}
        predicted = {"task-1": None}
        self.assertIsNone(gold["task-1"])
        self.assertEqual(score_decisions(gold, predicted)["decision_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()

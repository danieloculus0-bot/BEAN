"""Synthetic regression checks for paired Core learning-score interpretation."""
import unittest

from bean.evaluation.github_digital_cycle import _summary


def record(candidate, passive, grammar=None):
    correct = {"candidate": candidate, "passive": passive,
               "shuffled": 0, "always_zero": 0, "memory_ablated": 0}
    if grammar is not None:
        correct["grammar_matched"] = grammar
    return {
        "generation": 65, "source_sha": "synthetic-test",
        "family": "channel", "correct": correct, "abstentions": {},
        "learning_status": "provisional_rule",
        "learning_receipt_id": "synthetic-receipt",
        "prior_generation_transfer_correct": None,
        "scored_cases": 48, "evaluation_sha256": "synthetic-eval",
    }


class ControlAdvantageReceiptTests(unittest.TestCase):
    def test_perfect_candidate_tied_with_controls_is_not_memory_gain(self):
        summary = _summary([record(48, 48, 48)], new_evaluation=True)
        self.assertEqual(summary["candidate_correct_total"], 48)
        self.assertEqual(summary["candidate_minus_passive_correct_total"], 0)
        self.assertEqual(summary["candidate_minus_grammar_matched_correct_total"], 0)
        self.assertIs(summary["memory_specific_advantage_observed"], False)

    def test_candidate_advantage_is_explicit_and_signed(self):
        summary = _summary([record(38, 40, 32)], new_evaluation=True)
        self.assertEqual(summary["candidate_minus_passive_correct_total"], -2)
        self.assertEqual(summary["candidate_minus_grammar_matched_correct_total"], 6)
        self.assertIs(summary["memory_specific_advantage_observed"], True)

    def test_historical_missing_control_remains_unknown(self):
        summary = _summary([record(32, 30)], new_evaluation=False)
        self.assertIsNone(summary["candidate_minus_grammar_matched_correct_total"])
        self.assertIsNone(summary["memory_specific_advantage_observed"])


if __name__ == "__main__":
    unittest.main()

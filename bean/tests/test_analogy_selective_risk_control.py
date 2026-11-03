"""Synthetic selective-risk evaluation control for analogy recall.

A no-recall policy is not necessarily a failure: when no precedent is valid,
abstention is the correct action. This evaluates *decision* accuracy separately
from top-1 retrieval accuracy. No BEAN semantic improvement is asserted.
"""
import unittest


def score_decisions(gold, predictions):
    """Return coverage, selective accuracy, and all-case decision accuracy.

    gold maps task IDs to a valid precedent ID or None (no valid precedent).
    predictions maps the same IDs to a chosen ID or None (abstain).
    No candidate labels or model scores are used to derive the gold standard.
    """
    if not gold or set(gold) != set(predictions):
        raise ValueError("nonempty identical task IDs required")
    n = len(gold)
    answered = [key for key in gold if predictions[key] is not None]
    correct_answered = sum(predictions[k] == gold[k] for k in answered)
    correct_decisions = sum(predictions[k] == gold[k] for k in gold)
    return {
        "coverage": len(answered) / n,
        "selective_accuracy": (
            correct_answered / len(answered) if answered else None
        ),
        "decision_accuracy": correct_decisions / n,
        "answered": len(answered),
        "correct_decisions": correct_decisions,
    }


class SelectiveRiskNegativeControl(unittest.TestCase):
    def test_abstention_can_be_correct(self):
        # Labels assigned independently of the two simulated policies.
        gold = {"support": "evidence-A", "contradiction": None,
                "unrelated": None, "reversal": "evidence-B"}
        always_first = {key: "evidence-A" for key in gold}
        always_abstain = {key: None for key in gold}
        oracle = dict(gold)
        first = score_decisions(gold, always_first)
        abstain = score_decisions(gold, always_abstain)
        upper = score_decisions(gold, oracle)
        self.assertEqual(first["decision_accuracy"], 0.25)
        self.assertEqual(abstain["decision_accuracy"], 0.5)
        self.assertEqual(upper["decision_accuracy"], 1.0)
        self.assertEqual(abstain["coverage"], 0.0)
        self.assertIsNone(abstain["selective_accuracy"])
        self.assertEqual(upper["coverage"], 0.5)
        self.assertEqual(upper["selective_accuracy"], 1.0)

    def test_no_abstention_is_not_perfect(self):
        gold = {"negative": None}
        self.assertEqual(
            score_decisions(gold, {"negative": "candidate"})["decision_accuracy"],
            0.0,
        )
        self.assertEqual(
            score_decisions(gold, {"negative": None})["decision_accuracy"],
            1.0,
        )

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            score_decisions({}, {})
        with self.assertRaises(ValueError):
            score_decisions({"a": None}, {"b": None})


if __name__ == "__main__":
    unittest.main()

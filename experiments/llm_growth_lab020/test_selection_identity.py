"""Evaluator-owned contract: actual BEAN Core selector, original API preserved.

The LLM prompt contains the task and original source only, NOT this file.
Tests intentionally cover previously working behavior as well as the defect.
"""
import unittest
from bean.optimization.selection import ImprovementOpportunity, rank_improvements


def opportunity(name, *, impact=3, reproducibility=4, confidence=.75,
                risk=1, ready=True, evidence=("test:independent-001",)):
    return ImprovementOpportunity(
        identifier=name, description="Test-ready documented Core improvement",
        evidence_refs=evidence, impact=impact, reproducibility=reproducibility,
        confidence=confidence, risk=risk, validation_ready=ready)


class SelectionContract(unittest.TestCase):
    def test_exact_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([opportunity("alpha"), opportunity("alpha")])

    def test_same_identifier_different_whitespace_and_case_must_collide(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([opportunity("Fix-217"), opportunity(" fix-217 ")])

    def test_casefold_unicode_identity_must_collide(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([opportunity("Straße"), opportunity(" STRASSE ")])

    def test_existing_spelling_remains_unchanged_in_returned_result(self):
        result = rank_improvements([opportunity("  Legacy-A  ")])
        self.assertEqual(result[0].opportunity.identifier, "  Legacy-A  ")

    def test_valid_distinct_identifiers_are_not_rejected(self):
        self.assertEqual(len(rank_improvements([
            opportunity("ABC-100"), opportunity("ABC-101")])), 2)

    def test_high_scoring_ready_improvement_ranks_first(self):
        results = rank_improvements([
            opportunity("low", impact=1, reproducibility=1),
            opportunity("high", impact=5, reproducibility=5),
        ])
        self.assertEqual(results[0].opportunity.identifier, "high")

    def test_equal_scores_sort_lexically(self):
        results = rank_improvements([opportunity("z"), opportunity("a")])
        self.assertEqual([r.opportunity.identifier for r in results], ["a", "z"])

    def test_risk_budget_still_applies(self):
        results = rank_improvements([opportunity("high-risk", risk=4),
                                     opportunity("bounded", risk=2)])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].opportunity.identifier, "bounded")

    def test_not_ready_excluded(self):
        self.assertEqual(rank_improvements([opportunity("wait", ready=False)]), [])

    def test_confidence_invalid_rejected(self):
        with self.assertRaisesRegex(ValueError, "confidence"):
            opportunity("bad", confidence=float("nan"))

    def test_bool_reproducibility_rejected(self):
        with self.assertRaisesRegex(ValueError, "reproducibility"):
            opportunity("bad", reproducibility=True)

    def test_evidence_required(self):
        with self.assertRaisesRegex(ValueError, "evidence"):
            opportunity("bad", evidence=())

    def test_score_unchanged(self):
        result = rank_improvements([opportunity(
            "baseline-score", impact=3, reproducibility=4,
            confidence=.5, risk=1)])[0]
        self.assertEqual(result.score, 21.5)

    def test_duplicate_rejected_even_when_risk_filtered(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([opportunity("RISK", risk=5),
                               opportunity(" risk ", risk=1)])


if __name__ == "__main__":
    unittest.main()

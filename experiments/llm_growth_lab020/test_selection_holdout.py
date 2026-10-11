"""Additional holdout never used in model feedback or candidate selection."""
import unittest
from bean.optimization.selection import ImprovementOpportunity, rank_improvements


def op(name, risk=1):
    return ImprovementOpportunity(
        identifier=name, description="Independent real-world defect",
        evidence_refs=("holdout:source",), impact=4, reproducibility=4,
        confidence=.85, risk=risk, validation_ready=True)


class NewIdentityHoldout(unittest.TestCase):
    def test_tabs_and_newlines_collide_with_trimmed_id(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([op("\tHistory-9\n"), op("history-9")])

    def test_sharp_s_casefold_expansion(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([op("MASS"), op("maß")])

    def test_casefold_does_not_reject_distinct_diacritics(self):
        self.assertEqual(len(rank_improvements([op("resume"), op("résumé")])), 2)

    def test_empty_list_remains_supported(self):
        self.assertEqual(rank_improvements([]), [])

    def test_duplicate_in_risk_filtered_records_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([op("Audit-One", risk=5), op(" audit-one ", risk=0)])

    def test_original_identifier_preserved_for_audit(self):
        self.assertEqual(rank_improvements([op("  Finite-01 ")])[0]
                         .opportunity.identifier, "  Finite-01 ")

    def test_no_synthetic_auto_accept(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rank_improvements([op("Repo/Main"), op("REPO/MAIN")])


if __name__ == "__main__":
    unittest.main()

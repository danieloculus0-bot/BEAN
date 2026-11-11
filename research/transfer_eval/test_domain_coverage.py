"""Synthetic controls for domain breadth, not learned transfer results."""
import unittest
from research.transfer_eval.domain_coverage import domain_coverage


def row(case, family, domain, baseline=False, candidate=True):
    return {"case_id": case, "family_id": family, "target_domain": domain,
            "baseline_correct": baseline, "candidate_correct": candidate}


class DomainCoverageTests(unittest.TestCase):
    def test_one_domain_is_not_cross_domain(self):
        result = domain_coverage([row("a", "a", "alpha"), row("b", "b", "alpha")])
        self.assertFalse(result["cross_domain_supported"])

    def test_negative_domain_prevents_breadth_claim(self):
        result = domain_coverage([row("a", "a", "alpha"), row("b", "b", "beta", True, False)])
        self.assertFalse(result["cross_domain_supported"])
        self.assertEqual(result["domains"]["beta"]["family_losses"], 1)

    def test_shared_family_not_independent_replication(self):
        result = domain_coverage([row("a", "template", "alpha"), row("b", "template", "beta")])
        self.assertFalse(result["cross_domain_supported"])
        self.assertEqual(result["shared_dependency_families"], ["template"])

    def test_two_distinct_positive_domains_descriptive_only(self):
        result = domain_coverage([row("a", "a", "alpha"), row("b", "b", "beta")])
        self.assertTrue(result["cross_domain_supported"])
        self.assertIn("not_validated_transfer", result["claim"])

    def test_invalid_domain_rejected(self):
        with self.assertRaises(ValueError):
            domain_coverage([row("a", "a", " ")])


if __name__ == "__main__":
    unittest.main()

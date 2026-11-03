"""Synthetic split-leakage controls, not BEAN acquisition measurements."""
import unittest
from research.transfer_eval.split_leakage import audit_split

def row(case, family, source, receipt):
    return dict(case_id=case, family_id=family, source_sha=source, receipt_sha=receipt)

class SplitLeakageTests(unittest.TestCase):
    def setUp(self):
        self.train = [row("train", "template-A", "source-A", "receipt-A")]
        self.test = [row("test", "template-B", "source-B", "receipt-B")]

    def test_separate_metadata_is_descriptive_only(self):
        result = audit_split(iter(self.train), iter(self.test))
        self.assertTrue(result["heldout_separated"])
        self.assertIn("not_semantic_independence", result["claim"])

    def test_family_leakage_even_when_case_ids_differ(self):
        result = audit_split(self.train, [row("new", "template-A", "source-B", "receipt-B")])
        self.assertFalse(result["heldout_separated"])
        self.assertEqual(result["overlaps"]["family_id"], ["template-A"])

    def test_source_leakage_even_when_family_ids_differ(self):
        result = audit_split(self.train, [row("new", "template-B", "source-A", "receipt-B")])
        self.assertFalse(result["heldout_separated"])
        self.assertEqual(result["overlaps"]["source_sha"], ["source-A"])

    def test_receipt_reuse_is_not_new_evidence(self):
        result = audit_split(self.train, [row("new", "template-B", "source-B", "receipt-A")])
        self.assertFalse(result["heldout_separated"])

    def test_duplicate_or_missing_metadata_fails_closed(self):
        with self.assertRaises(ValueError):
            audit_split(self.train, self.test * 2)
        with self.assertRaises(ValueError):
            audit_split(self.train, [dict(self.test[0], source_sha="")])
        with self.assertRaises(ValueError):
            audit_split([], self.test)

if __name__ == "__main__":
    unittest.main()

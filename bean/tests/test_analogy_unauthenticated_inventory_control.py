"""Negative control: inventory agreement is not authenticated source provenance.

The evaluator checks internal agreement of supplied IDs and digest strings, not
whether either was obtained from canonical SQLite/JSONL receipts. This is an
intentional, passing falsification test, NOT evidence of BEAN intelligence.
"""
import hashlib
import unittest

from bean.tests.test_analogy_verified_inventory_control import score_verified_decisions


class UnauthenticatedInventoryNegativeControl(unittest.TestCase):
    def test_fabricated_inventory_can_score_perfectly(self):
        # Both label and inventory are invented by the same hypothetical actor.
        # Even a well-formed SHA256 digest is not a verified event-store receipt.
        invented = b"synthetic invented event, never committed to BEAN event history"
        digest = hashlib.sha256(invented).hexdigest()
        gold = {"case": "invented-receipt"}
        predictions = {"case": ("invented-receipt", digest)}
        inventory = {"case": {"invented-receipt": digest}}
        result = score_verified_decisions(gold, predictions, inventory)
        self.assertEqual(result["decision_accuracy"], 1.0)
        self.assertEqual(result["invalid_provenance_tasks"], ())
        # The actual correct conclusion is limited: the three caller-supplied
        # structures agree. No canonical event lookup or signature occurred.


if __name__ == "__main__":
    unittest.main()

"""Structural checks for BEAN's learning receipt ledger."""
from __future__ import annotations

import json
import unittest

from scripts.validate_learning_ledger import validate_entries


def example() -> dict:
    row = {
        "lesson_id": "TEST-001",
        "recorded_date": "2026-10-18",
        "title": "One observed outcome is not generalization",
        "status": "inconclusive",
        "domain": "research",
        "observation": "An output was recorded.",
        "evidence_type": "synthetic",
        "evidence_urls": ["https://example.org/source"],
        "how_learned": "An isolated check exposed a missing control.",
        "what_changed": "A research note was written.",
        "actual_learning_mechanism": "human review",
        "validated_outcome": "not demonstrated",
        "transfer_test": "held out replication",
        "limitations": "only one example",
        "promotion_state": "research_only",
        "causal_learning_demonstrated": False,
        "baseline_run_ref": None,
        "treatment_run_ref": None,
        "heldout_eval_ref": None,
        "mechanism_artifact_ref": None,
    }
    return row


class LearningLedgerContractTests(unittest.TestCase):
    def test_valid_noncausal_receipt(self):
        self.assertEqual(len(validate_entries([json.dumps(example())])), 1)

    def test_real_repository_ledger(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        rows = validate_entries(
            (root / "research" / "learning_ledger.jsonl")
            .read_text(encoding="utf-8").splitlines()
        )
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all(not x["causal_learning_demonstrated"] for x in rows))

    def test_duplicate_id_fails(self):
        line = json.dumps(example())
        with self.assertRaisesRegex(ValueError, "duplicated"):
            validate_entries([line, line])

    def test_false_learning_claim_without_proof_fails(self):
        row = example()
        row["causal_learning_demonstrated"] = True
        row["status"] = "independently_replicated"
        with self.assertRaisesRegex(ValueError, "lacks causal proof"):
            validate_entries([json.dumps(row)])

    def test_not_replicated_learning_claim_fails(self):
        row = example()
        row["causal_learning_demonstrated"] = True
        for key in (
            "baseline_run_ref", "treatment_run_ref", "heldout_eval_ref",
            "mechanism_artifact_ref"
        ):
            row[key] = "https://example.org/receipt"
        with self.assertRaisesRegex(ValueError, "independently_replicated"):
            validate_entries([json.dumps(row)])

    def test_empty_or_missing_provenance_fails(self):
        row = example()
        row["evidence_urls"] = []
        with self.assertRaisesRegex(ValueError, "evidence_urls"):
            validate_entries([json.dumps(row)])

    def test_invalid_json_fails(self):
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            validate_entries(["{invalid"])

    def test_valid_replicated_receipt_structurally_accepted(self):
        row = example()
        row["status"] = "independently_replicated"
        row["causal_learning_demonstrated"] = True
        for key in (
            "baseline_run_ref", "treatment_run_ref", "heldout_eval_ref",
            "mechanism_artifact_ref"
        ):
            row[key] = "https://example.org/receipt"
        self.assertEqual(len(validate_entries([json.dumps(row)])), 1)


if __name__ == "__main__":
    unittest.main()

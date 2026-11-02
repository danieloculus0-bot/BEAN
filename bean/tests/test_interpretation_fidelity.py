"""Regression: a user's correction reaches actual model context without invented meaning."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bean.learning.interpretation_fidelity import (
    context_for_interpretation, has_interpretation_correction,
)
from bean.learning.reasoning_service import NativeReasoningService


class OfflineProvider:
    model_id = "synthetic-provider"
    provider_kind = "synthetic_fixture"
    adapter_name = "local_llamacpp"

    def __init__(self):
        self.calls = []

    def complete(self, query, context):
        self.calls.append((query, context))
        return "I do not have enough evidence to infer the earlier meaning."


class InterpretationFidelityTests(unittest.TestCase):
    def test_normal_context_remains_unchanged(self):
        self.assertFalse(has_interpretation_correction("Please review this fictional setup."))
        self.assertEqual(
            context_for_interpretation("Please review this fictional setup.", "Evidence A"),
            "Evidence A",
        )

    def test_feedback_variants_do_not_imply_intent(self):
        for request in (
            "You don't get me.",
            "You do not understand me",
            "That's not what I meant",
            "You're missing my point.",
        ):
            with self.subTest(request=request):
                self.assertTrue(has_interpretation_correction(request))
                context = context_for_interpretation(request, "source-linked note")
                self.assertIn("earlier words are absent", context)
                self.assertIn("ask one precise clarification", context)
                self.assertTrue(context.endswith("source-linked note"))
        self.assertFalse(has_interpretation_correction("I don't understand this blueprint"))

    def test_native_core_model_receives_correction_and_journals_exact_query(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            provider = OfflineProvider()
            core = NativeReasoningService(path, model=provider)
            try:
                request = "You don't get me. You're substituting your own example."
                result = core.reason(
                    domain="conversation", task_ref="intent-correction",
                    query=request,
                )
                self.assertEqual(result["provider_kind"], "synthetic_fixture")
                self.assertEqual(provider.calls[0][0], request)
                self.assertIn("USER INTERPRETATION CORRECTION", provider.calls[0][1])
                self.assertIn("not verified", provider.calls[0][1])
                events = core.bank.journal.events()
                receipts = [e["data"] for e in events if e["kind"] == "inference"]
                self.assertEqual(len(receipts), 1)
                self.assertEqual(receipts[0]["query"], request)
                self.assertFalse(receipts[0]["verified_outcome"])

                normal = core.reason(
                    domain="conversation", task_ref="routine",
                    query="Review synthetic gauge readings",
                )
                self.assertNotEqual(result["receipt_id"], normal["receipt_id"])
                self.assertEqual(provider.calls[1][0], "Review synthetic gauge readings")
                self.assertNotIn("USER INTERPRETATION CORRECTION", provider.calls[1][1])
            finally:
                core.close()

            reopened = NativeReasoningService(path, model=None)
            try:
                saved = [e["data"] for e in reopened.bank.journal.events()
                         if e["kind"] == "inference"]
                self.assertEqual(saved[0]["query"], request)
                self.assertEqual(len(saved), 2)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()

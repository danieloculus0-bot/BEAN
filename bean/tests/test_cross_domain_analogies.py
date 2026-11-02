"""Real Core cross-domain recall, provider context, provenance and restart tests.

These synthetic cases prove bounded evidence retrieval, NOT that a policy
successfully transfers to a different task or that BEAN is AGI.
"""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from bean.learning.reasoning_service import (
    NativeReasoningService, register_native_reasoning_handlers,
)


class OfflineModel:
    model_id = "original-synthetic-test-only"
    provider_kind = "synthetic_fixture"
    adapter_name = "local_llamacpp"

    def __init__(self):
        self.calls = []

    def complete(self, query, context):
        self.calls.append((query, context))
        return "Candidate precedent observed; target outcome not established."


class Inbox:
    def __init__(self):
        self.handlers = {}

    def register(self, key, handler):
        self.handlers[key] = handler

    def call(self, key, **kwargs):
        return self.handlers[key](SimpleNamespace(args=kwargs), "test-session")


class CrossDomainRecallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "native.sqlite"
        self.model = OfflineModel()
        self.core = NativeReasoningService(self.db, model=self.model)
        self.addCleanup(self.core.close)
        self.source = self.core.retain_skill(
            domain="maintenance",
            name="capacity fallback",
            steps=[
                "Measure equipment capacity before dispatch",
                "Select a backup resource when equipment capacity is exhausted",
            ],
            passed=True,
            evidence_refs=["fixture:maintenance-observation-a"],
        )["lesson_id"]
        self.core.retain_skill(
            domain="scheduling",
            name="same-domain capacity",
            steps=["Assess equipment capacity", "Use local backup resource"],
            passed=True, evidence_refs=["fixture:scheduling-same-domain"],
        )
        self.core.retain_skill(
            domain="calibration",
            name="restricted maintenance concept",
            steps=["Measure equipment capacity", "Select a backup resource"],
            passed=True,
            evidence_refs=["bridge_concept:restricted-measuring", "fixture:restricted"],
        )
        self.core.retain_skill(
            domain="payroll",
            name="unrelated practice",
            steps=["Verify hours", "Review payments"],
            passed=True, evidence_refs=["fixture:payroll"],
        )

    def test_cross_domain_recall_preserves_origin_and_rejects_generic_matches(self):
        question = "Review equipment capacity and backup resource in scheduling"
        before = len(self.core.bank.journal.events())
        candidates = self.core.recall_analogies(
            domain="scheduling", query=question)
        self.assertEqual(len(candidates), 1)
        hit = candidates[0]
        self.assertEqual(hit["lesson_id"], self.source)
        self.assertEqual(hit["source_domain"], "maintenance")
        self.assertEqual(hit["observed_outcome"],
                         "host_reported_success_not_verified")
        self.assertIn("capacity", hit["matched_terms"])
        self.assertEqual(hit["evidence_refs"],
                         ["fixture:maintenance-observation-a"])
        self.assertFalse(hit["independently_verified_transfer"])
        self.assertFalse(hit["safe_to_apply_without_target_test"])
        self.assertEqual(before, len(self.core.bank.journal.events()))
        self.assertEqual(self.core.recall_analogies(
            domain="scheduling", query="Can you help?"), [])
        with self.assertRaises(ValueError):
            self.core.recall_analogies(domain="scheduling", query=question,
                                      limit=0)

    def test_native_inference_opt_in_carries_precise_source_and_receipt(self):
        q = "Review equipment capacity and backup resource in scheduling"
        cold = self.core.reason(domain="scheduling", task_ref="cold", query=q)
        self.assertNotIn("POSSIBLE_OTHER_DOMAIN_PRECEDENTS", self.model.calls[0][1])
        self.assertEqual(self.model.calls[0][0], q)
        opt = self.core.reason(domain="scheduling", task_ref="with-precedent",
                               query=q, include_analogies=True)
        self.assertEqual(self.model.calls[1][0], q)
        context = self.model.calls[1][1]
        self.assertIn("POSSIBLE_OTHER_DOMAIN_PRECEDENTS", context)
        self.assertIn("UNVERIFIED", context)
        self.assertIn(self.source, context)
        self.assertIn("fixture:maintenance-observation-a", context)
        self.assertNotIn("fixture:scheduling-same-domain", context)
        self.assertNotIn("fixture:restricted", context)
        self.assertNotEqual(cold["receipt_id"], opt["receipt_id"])
        records = [row["data"] for row in self.core.bank.journal.events()
                   if row["kind"] == "inference"]
        self.assertEqual(len(records), 2)
        self.assertNotIn("cross_domain_candidate_ids", records[0])
        self.assertEqual(records[1]["cross_domain_candidate_ids"], [self.source])
        self.assertFalse(records[1]["cross_domain_transfer_verified"])
        self.assertTrue(records[1]["cross_domain_recall_opt_in"])
        self.assertEqual(records[1]["query"], q)
        self.assertFalse(records[1]["verified_outcome"])
        with self.assertRaisesRegex(ValueError, "boolean"):
            self.core.reason(domain="scheduling", task_ref="bad", query=q,
                             include_analogies="yes")
        self.assertEqual(len(self.model.calls), 2)

        self.core.close()
        later = NativeReasoningService(self.db, model=None)
        try:
            again = later.recall_analogies(domain="scheduling", query=q)
            self.assertEqual(again[0]["lesson_id"], self.source)
            record = [e["data"] for e in later.bank.journal.events()
                      if e["kind"] == "inference"][-1]
            self.assertEqual(record["receipt_id"], opt["receipt_id"])
        finally:
            later.close()

    def test_real_inbox_command_exposes_same_candidates_without_model_call(self):
        inbox = Inbox()
        register_native_reasoning_handlers(inbox, self.core)
        result = inbox.call("reasoning_analogies", domain="scheduling",
                            query="Review equipment capacity and backup resource")
        self.assertEqual([x["lesson_id"] for x in result], [self.source])
        self.assertEqual(self.model.calls, [])

    def test_ambiguous_or_insufficient_overlap_never_invents_transfer(self):
        self.assertEqual(self.core.recall_analogies(
            domain="scheduling", query="backup"), [])
        self.assertEqual(self.core.recall_analogies(
            domain="scheduling", query="monthly payroll taxes"), [])
        self.assertEqual(self.core.recall_analogies(
            domain="scheduling", query="inspect datums in the blueprint"), [])
        # The confined Bridge lesson cannot leak merely through shared words.
        result = self.core.recall_analogies(
            domain="scheduling", query="equipment capacity backup resource")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["lesson_id"], self.source)


if __name__ == "__main__":
    unittest.main()

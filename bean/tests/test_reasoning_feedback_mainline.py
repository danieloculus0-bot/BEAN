"""Real BEAN integration: selected answer -> reported outcome -> saved lesson."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json

from bean.learning.reasoning_service import (
    NativeReasoningService, register_native_reasoning_handlers,
)
from bean.runtime.inbox import CommandInbox


class Provider:
    provider_kind = "synthetic_fixture"
    model_id = "offline-only-standin"

    def __init__(self):
        self.available = True
        self.calls = []

    def complete(self, question, context):
        self.calls.append((question, context))
        if not self.available:
            raise RuntimeError("PRIVATE_SOME_MODEL_SECRET")
        return "UNSORTED"


class FeedbackLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "lesson.sqlite3"
        self.provider = Provider()
        self.service = NativeReasoningService(self.path, model=self.provider)
        self.addCleanup(self.service.close)
        self.inbox = CommandInbox(Path(self.temp.name) / "inbox")
        register_native_reasoning_handlers(self.inbox, self.service)

    def seed(self):
        self.service.reflect(
            domain="sorting", task_id="dev-error", observed="Z,B",
            expected="B,Z", adjustment_hypothesis="SORT_COMMAS sort letters",
            evidence_refs=["source:initial"])
        self.service.retain_skill(
            domain="sorting", name="SORT_COMMAS", passed=True,
            steps=["SORT_COMMAS sorting"], evidence_refs=["source:known"])
        self.service.propose_instruction(
            domain="sorting", instruction="SORT_COMMAS",
            evidence_refs=["source:prompt"])
        self.service.reflect(
            domain="other", task_id="other-case",
            observed="hot", expected="cold",
            adjustment_hypothesis="other unrelated rule", evidence_refs=["source:control"])
        rows = [
            {"task_id": task, "arm": arm, "replicate": 0,
             "passed": arm == "reflection", "evidence_ref": f"{task}:{arm}"}
            for task in ("train-a", "train-b")
            for arm in ("cold", "reflection", "skill", "prompt", "placebo")
        ]
        choice = self.service.choose_from_outcomes(
            domain="sorting", rows=rows,
            evaluator_id="fixture", dataset_id="training-not-holdout")
        self.assertEqual(choice["arm"], "reflection")

    def test_failed_answer_becomes_durable_correctable_lesson(self):
        self.seed()
        old = self.service.reason(domain="sorting", task_ref="test-a",
                                  query="SORT_COMMAS sort new letters")
        self.assertEqual(old["answer"], "UNSORTED")
        outcome = self.service.feedback(
            receipt_id=old["receipt_id"], expected="SORTED",
            adjustment_hypothesis="SORT_COMMAS order alphabetically",
            evidence_refs=["evaluator:observed-test-a"])
        self.assertFalse(outcome["matched"])
        self.assertTrue(outcome["correction_added"])
        self.assertTrue(outcome["new_feedback"])
        again = self.service.feedback(
            receipt_id=old["receipt_id"], expected="SORTED",
            adjustment_hypothesis="SORT_COMMAS order alphabetically",
            evidence_refs=["evaluator:observed-test-a"])
        self.assertFalse(again["new_feedback"])
        self.assertEqual(self.service.status()["feedback_receipts"], 1)
        self.service.close()
        resumed = NativeReasoningService(self.path, model=self.provider)
        try:
            self.assertEqual(resumed.status()["feedback_receipts"], 1)
            corrections = resumed.recall(domain="sorting", query="SORT_COMMAS",
                                         strategy="reflection")
            self.assertTrue(any(old["receipt_id"] in ",".join(item["evidence_refs"])
                                for item in corrections))
            decision = resumed.decide(domain="sorting", task_ref="next",
                                      query="SORT_COMMAS order letters")
            self.assertEqual(decision["selected_strategy"], "reflection")
        finally:
            resumed.close()

    def test_positive_outcome_is_stored_without_fabricating_new_correction(self):
        self.seed()
        prior = self.service.reason(domain="sorting", task_ref="test-positive",
                                    query="SORT_COMMAS sort example")
        match = self.service.feedback(
            receipt_id=prior["receipt_id"], expected="UNSORTED",
            evidence_refs=["evaluator:positive-test"])
        self.assertTrue(match["matched"])
        self.assertFalse(match["correction_added"])
        self.assertEqual(self.service.status()["feedback_receipts"], 1)
        self.assertEqual(self.service.status()["selected_strategies"], 1)

    def test_repeated_identical_answers_get_unique_replayable_receipts(self):
        self.seed()
        first = self.service.reason(
            domain="sorting", task_ref="same-task",
            query="SORT_COMMAS sort new letters")
        second = self.service.reason(
            domain="sorting", task_ref="same-task",
            query="SORT_COMMAS sort new letters")
        self.assertEqual(first["answer"], second["answer"])
        self.assertNotEqual(first["receipt_id"], second["receipt_id"])
        for idx, reply in enumerate((first, second)):
            observed = self.service.feedback(
                receipt_id=reply["receipt_id"], expected="UNSORTED",
                evidence_refs=["evaluator:case-" + str(idx)])
            self.assertTrue(observed["new_feedback"])
            self.assertTrue(observed["matched"])
        self.assertEqual(self.service.status()["feedback_receipts"], 2)
        self.service.close()
        reopened = NativeReasoningService(self.path, model=self.provider)
        try:
            receipts = [x["data"]["receipt_id"]
                        for x in reopened.bank.journal.events()
                        if x["kind"] == "inference"]
            self.assertEqual(len(receipts), len(set(receipts)))
            self.assertEqual(reopened.status()["feedback_receipts"], 2)
        finally:
            reopened.close()

    def test_provider_error_is_recorded_without_secret_string_or_false_answer(self):
        self.seed()
        self.provider.available = False
        with self.assertRaisesRegex(RuntimeError, "PRIVATE_SOME_MODEL_SECRET"):
            self.service.reason(domain="sorting", task_ref="outage",
                                query="SORT_COMMAS why failed")
        self.assertEqual(self.service.status()["failed_inference_attempts"], 1)
        receipts = [x["data"] for x in self.service.bank.journal.events()
                    if x["kind"] == "inference"]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["status"], "failed")
        self.assertEqual(receipts[0]["answer"], "")
        self.assertEqual(receipts[0]["exception_class"], "RuntimeError")
        self.assertNotIn("PRIVATE_SOME_MODEL_SECRET", json.dumps(receipts))

    def test_unknown_inference_cannot_create_fake_feedback(self):
        self.seed()
        with self.assertRaisesRegex(ValueError, "completed BEAN reasoning receipt"):
            self.service.feedback(receipt_id="a" * 64, expected="yes",
                                  evidence_refs=["truth:source"])

    def test_model_request_invalid_evidence_is_rejected_before_provider_call(self):
        with self.assertRaisesRegex(ValueError, "references required"):
            self.service.generate(domain="sorting", task_ref="candidate",
                                  examples=[{"question":"a","answer":"b"},
                                            {"question":"c","answer":"d"}],
                                  evidence_refs=[])
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(self.service.status()["inference_receipts"], 0)

    def test_inbox_invalid_command_never_logs_raw_prompt(self):
        invalid = self.inbox.inbox_dir / "invalid.json"
        invalid.write_text(json.dumps({"command": "", "args": {
            "token": "PRIVATE_VALUE_DO_NOT_LOG"}}))
        entries = []
        with patch("bean.runtime.inbox.log_event",
                   side_effect=lambda *args, **kwargs: entries.append([args, kwargs])):
            result = self.inbox.poll("session-test")
        self.assertEqual(result[0]["status"], "no_command")
        self.assertNotIn("PRIVATE_VALUE_DO_NOT_LOG", json.dumps(entries))


if __name__ == "__main__":
    unittest.main()

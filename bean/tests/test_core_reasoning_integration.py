"""Integration contract: BEAN Core reasoning learning is real, persisted, callable.

Fixtures are explicitly synthetic and do not establish general reasoning
improvement. This tests that *main's* runtime/host interfaces connect the
previously experimental parts without silently pretending to call a model.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from bean.learning import NativeReasoningService
from bean.learning.reasoning_service import register_native_reasoning_handlers
from bean.reasoning.reasoning_engine import adapter_from_name
from bean.reasoning.openrouter_provider import OpenRouterProvider


class FixtureModel:
    provider_kind = "synthetic_fixture"
    model_id = "unit-standin-not-real"

    def __init__(self):
        self.calls = []

    def complete(self, question, context):
        self.calls.append({"question": question, "context": context})
        if question.startswith("Induce a reusable procedure"):
            return "SORT_COMMAS order comma-delimited tags alphabetically"
        if "SORT_COMMAS" in context:
            return "SORTED"
        return "UNKNOWN"


class FakeInbox:
    def __init__(self):
        self.handlers = {}

    def register(self, name, fn):
        self.handlers[name] = fn

    def call(self, command, **args):
        return self.handlers[command](SimpleNamespace(args=args), "session-fixture")


class HTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, maximum):
        return json.dumps(self.payload).encode("utf-8")


class NativeCoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "reasoning.sqlite"
        self.model = FixtureModel()
        self.service = NativeReasoningService(self.db, model=self.model)
        self.addCleanup(self.service.close)
        self.inbox = FakeInbox()
        register_native_reasoning_handlers(self.inbox, self.service)

    def seed(self):
        self.inbox.call("reasoning_reflect", domain="sorting", task_id="dev-a",
                        observed="unsorted", expected="sorted",
                        adjustment_hypothesis="SORT_COMMAS order comma tags alphabetically",
                        evidence_refs=["observed:dev-a"])
        self.inbox.call("reasoning_skill", domain="sorting", name="SORT_COMMAS",
                        steps=["SORT_COMMAS sort comma tags"], passed=True,
                        evidence_refs=["observed:validation"])
        self.inbox.call("reasoning_instruction", domain="sorting",
                        instruction="SORT_COMMAS sort comma tags",
                        evidence_refs=["observed:instruction"])
        self.inbox.call("reasoning_reflect", domain="unrelated", task_id="dev-b",
                        observed="up", expected="down",
                        adjustment_hypothesis="This is unrelated to comma sorting",
                        evidence_refs=["control:unrelated"])

    @staticmethod
    def scored_selection():
        return [
            {"task_id": task, "arm": arm, "replicate": 0,
             "passed": arm == "reflection",
             "evidence_ref": task + ":" + arm}
            for task in ("dev-check-a", "dev-check-b")
            for arm in ("cold", "placebo", "reflection", "skill", "prompt")
        ]

    def test_full_runtime_command_path_then_restart_and_use_selected_lesson(self):
        self.seed()
        choice = self.inbox.call(
            "reasoning_compare", domain="sorting",
            rows=self.scored_selection(), evaluator_id="fixture-independent",
            dataset_id="development-fixture-1")
        self.assertEqual(choice["arm"], "reflection")
        decision = self.inbox.call(
            "reasoning_decide", domain="sorting",
            task_ref="fresh-case", query="SORT_COMMAS sort comma tags")
        self.assertEqual(decision["selected_strategy"], "reflection")
        self.assertEqual(len(decision["lessons"]), 1)
        reply = self.inbox.call(
            "reasoning_reason", domain="sorting",
            task_ref="fresh-case", query="SORT_COMMAS sort comma tags")
        self.assertEqual(reply["answer"], "SORTED")
        self.assertEqual(reply["provider_kind"], "synthetic_fixture")
        self.assertFalse(reply["verified_outcome"])
        self.assertEqual(self.service.status()["inference_receipts"], 1)
        self.assertIn("SORT_COMMAS", self.model.calls[-1]["context"])
        original_trial = decision["selection_trial_hash"]
        self.service.close()
        reopened = NativeReasoningService(self.db, model=self.model)
        try:
            second = reopened.reason(
                domain="sorting", task_ref="after-restart",
                query="SORT_COMMAS sort comma tags")
            self.assertEqual(second["answer"], "SORTED")
            self.assertEqual(second["decision"]["selection_trial_hash"], original_trial)
            self.assertEqual(second["decision"]["lessons"], decision["lessons"])
            self.assertEqual(reopened.status()["inference_receipts"], 2)
            self.assertEqual(reopened.status()["selected_strategies"], 1)
        finally:
            reopened.close()

    def test_generate_retains_model_authored_candidate_not_verified_learning(self):
        result = self.inbox.call("reasoning_generate", domain="sorting",
            task_ref="examples-a",
            examples=[
                {"question": "sort c,a", "answer": "a,c"},
                {"question": "sort d,b", "answer": "b,d"}],
            evidence_refs=["development:dataset-1"])
        self.assertIn("SORT_COMMAS", result["rule"])
        self.assertTrue(result["unverified"])
        self.assertTrue(result["candidate"]["new"])
        self.assertEqual(self.service.status()["inference_receipts"], 1)
        self.assertEqual(self.service.status()["selected_strategies"], 0)
        self.assertEqual(
            self.inbox.call("reasoning_recall", domain="sorting",
                            query="SORT_COMMAS", strategy="prompt")[0]["strategy"],
            "prompt")
        with self.assertRaisesRegex(ValueError, "No measured strategy selection"):
            self.service.reason(domain="sorting", task_ref="ungraded",
                                query="SORT_COMMAS sort comma tags")

    def test_no_model_produces_no_fabricated_answer_and_unknown_provider_fails(self):
        self.service.close()
        real = NativeReasoningService(Path(self.tmp.name) / "no-model.db")
        try:
            with self.assertRaisesRegex(ValueError, "No reasoning model configured"):
                real.generate(domain="sorting", task_ref="missing",
                              examples=[
                                  {"question": "a", "answer": "b"},
                                  {"question": "c", "answer": "d"}],
                              evidence_refs=["source:dev"])
            self.assertEqual(real.status()["inference_receipts"], 0)
        finally:
            real.close()
        with self.assertRaisesRegex(ValueError, "Unknown BEAN reasoning provider"):
            adapter_from_name("nemotron-typo")
        self.assertEqual(adapter_from_name("mock").adapter_name, "mock")

    def test_pinned_openrouter_reply_is_only_provider_text_not_truth(self):
        captured = []
        def request(req, timeout=90):
            body = json.loads(req.data.decode())
            self.assertEqual(body["model"],
                             "nvidia/nemotron-3-ultra-550b-a55b:free")
            self.assertIn("BEAN lesson", body["messages"][1]["content"])
            self.assertNotIn("fake-key", req.data.decode())
            captured.append(body)
            return HTTPResponse({
                "id": "unit-provider-reply",
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "choices": [{"message": {"content": "SORTED"}}],
            })
        provider = OpenRouterProvider(api_key="fake-key", requester=request)
        result = provider.complete("Sort a,b", "BEAN lesson")
        self.assertEqual(result["raw_text"], "SORTED")
        self.assertEqual(result["provider_response_id"], "unit-provider-reply")
        self.assertTrue(result["ok"])
        self.assertEqual(len(captured), 1)
        with self.assertRaisesRegex(ValueError, "explicitly free"):
            OpenRouterProvider(model_name="paid-model", api_key="fake-key")


if __name__ == "__main__":
    unittest.main()

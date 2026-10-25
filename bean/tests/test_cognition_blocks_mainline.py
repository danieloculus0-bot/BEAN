"""Cognition block adoption is actual Core inbox wiring, not a separate demo."""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from bean.modules.builtin import register_core_cognition_handlers, numeric_context


class FakeInbox:
    def __init__(self):
        self.handlers = {}

    def register(self, name, handler):
        self.handlers[name] = handler

    def call(self, command, **args):
        return self.handlers[command](SimpleNamespace(args=args), "session-test")


class StubReasoningService:
    def __init__(self):
        self.requests = []

    def reason(self, *, domain, task_ref, query):
        self.requests.append({"domain": domain, "task_ref": task_ref, "query": query})
        return {"answer": "BEAN-selected", "provider_kind": "synthetic_fixture"}


class CognitionBridgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.inbox = FakeInbox()
        self.reasoning = StubReasoningService()
        register_core_cognition_handlers(
            self.inbox, {"native_reasoning_service": self.reasoning})

    def test_full_command_registration_and_one_reasoning_owner(self):
        self.assertEqual(set(self.inbox.handlers), {
            "cognition_observe_experiment", "cognition_memory_recall",
            "cognition_numeric_context", "cognition_drive_status",
            "cognition_reason"})
        result = self.inbox.call("cognition_reason", domain="inspection",
                                 task_ref="candidate-001", query="measure tolerance")
        self.assertEqual(result["answer"], "BEAN-selected")
        self.assertEqual(self.reasoning.requests, [{
            "domain": "inspection", "task_ref": "candidate-001",
            "query": "measure tolerance"}])

    def test_numeric_bounded_and_stable(self):
        out = self.inbox.call("cognition_numeric_context",
                              history=[1, 4, -2], window=2)
        self.assertEqual(out["mean"], 1.0)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["last"], -2.0)
        self.assertEqual(out["trend"], "up")
        for history in ([float("nan")], [float("inf")], [1] * 10001):
            with self.assertRaises(ValueError):
                numeric_context({"history": history}, {})

    def test_reasoning_disabled_is_explicit(self):
        inbox = FakeInbox()
        register_core_cognition_handlers(inbox, {})
        with self.assertRaisesRegex(RuntimeError, "not enabled"):
            inbox.call("cognition_reason", domain="test", task_ref="a", query="b")


if __name__ == "__main__":
    unittest.main()

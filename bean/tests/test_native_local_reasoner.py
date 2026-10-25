"""Prove native BEAN reasoning survives restart with zero model/API requests.

Synthetic examples establish structural rule induction only. They are not
evidence that BEAN solves arbitrary language tasks without neural inference.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bean.learning.reasoning_service import NativeReasoningService, register_native_reasoning_handlers
from bean.reasoning.openrouter_provider import OpenRouterProvider


class CountingModel:
    model_id = "fixture-counting"
    provider_kind = "synthetic_fixture"
    def __init__(self):
        self.calls = 0
    def complete(self, prompt, context):
        self.calls += 1
        return "unneeded-model-answer"


class Inbox:
    def __init__(self):
        self.handlers = {}
    def register(self, name, fn):
        self.handlers[name] = fn
    def call(self, name, **kwargs):
        return self.handlers[name](SimpleNamespace(args=kwargs), "offline")


TAG_TRAIN = [
    {"question": "ORCHID-7 tags A3 B9 C5", "answer": "BCA"},
    {"question": "ORCHID-7 tags X7 Q1 D5", "answer": "XDQ"},
    {"question": "ORCHID-7 tags K2 L8 M4", "answer": "LMK"},
]
GAUGE_TRAIN = [
    {"question": "HARBOR-4 A=12 B=7 C=19", "answer": "A"},
    {"question": "HARBOR-4 D=10 E=20 F=15", "answer": "F"},
    {"question": "HARBOR-4 G=15 H=22 J=4", "answer": "G"},
]


class NativeLocalReasonerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "bean-local.sqlite3"
        self.fake = CountingModel()
        self.core = NativeReasoningService(self.db, model=self.fake)
        self.addCleanup(self.core.close)
        self.inbox = Inbox()
        register_native_reasoning_handlers(self.inbox, self.core)

    def learn(self, domain, examples):
        return self.inbox.call(
            "reasoning_learn_local", domain=domain, task_ref="development-v1",
            examples=examples, evidence_refs=["fixture:development-examples-v1"])

    def test_unseen_tag_problem_uses_retained_rule_with_no_model_after_restart(self):
        cold = self.inbox.call("reasoning_auto", domain="routing",
                               task_ref="cold", query="ORCHID-7 tags R7 C9 F2")
        self.assertEqual(cold["status"], "abstain")
        self.assertTrue(cold["external_provider_skipped"])
        learned = self.learn("routing", TAG_TRAIN)
        self.assertEqual(learned["operation"], "digit_desc")
        self.assertEqual(learned["status"], "learned_local_rule")
        current = self.inbox.call("reasoning_auto", domain="routing",
                                 task_ref="heldout-1", query="ORCHID-7 tags R7 C9 F2")
        self.assertEqual(current["answer"], "CRF")
        self.assertEqual(current["status"], "locally_solved")
        self.assertFalse(current["model_invoked"])
        self.assertEqual(current["external_cost_usd"], 0)
        self.assertEqual(self.fake.calls, 0)
        self.assertEqual(self.core.status()["native_symbolic_rules"], 1)
        self.assertEqual(self.core.status()["native_symbolic_inferences"], 1)
        self.assertIn("apply:digit_desc", current["trace"])
        self.core.close()
        resumed = NativeReasoningService(self.db, model=None)
        try:
            next_one = resumed.reason_auto(
                domain="routing", task_ref="heldout-2",
                query="ORCHID-7 tags T8 E4 Z7")
            self.assertEqual(next_one["answer"], "TZE")
            self.assertEqual(resumed.status()["native_symbolic_inferences"], 2)
            self.assertFalse(resumed.status()["model_configured"])
            self.assertNotEqual(next_one["receipt_id"], current["receipt_id"])
        finally:
            resumed.close()

    def test_independent_median_rule_and_wrong_domain_abstain(self):
        s = self.learn("gauges", GAUGE_TRAIN)
        self.assertEqual(s["operation"], "median")
        correct = self.core.reason_auto(
            domain="gauges", task_ref="unseen", query="HARBOR-4 P=30 S=12 T=22")
        self.assertEqual(correct["answer"], "T")
        unrelated = self.core.reason_auto(
            domain="routing", task_ref="unseen", query="HARBOR-4 P=30 S=12 T=22")
        self.assertEqual(unrelated["status"], "abstain")
        self.assertEqual(self.fake.calls, 0)

    def test_ambiguous_or_contradictory_teaching_cannot_become_a_rule(self):
        ambiguous = [
            {"question": "SORT tags A1 B2 C3", "answer": "ABC"},
            {"question": "SORT tags D1 E2 F3", "answer": "DEF"},
            {"question": "SORT tags G1 H2 J3", "answer": "GHJ"},
        ]
        response = self.learn("ambiguous", ambiguous)
        self.assertEqual(response["status"], "abstain")
        self.assertEqual(response["reason"], "ambiguous_hypothesis")
        self.assertEqual(self.core.status()["native_symbolic_rules"], 0)
        broken = TAG_TRAIN[:-1] + [{
            "question": TAG_TRAIN[-1]["question"], "answer": "INCORRECT"}]
        bad = self.learn("broken", broken)
        self.assertEqual(bad["reason"], "observations_contradict_all_candidates")
        self.assertEqual(self.core.status()["native_symbolic_rules"], 0)

    def test_no_provider_fallback_without_explicit_permission(self):
        no_network = self.core.reason_auto(
            domain="no-matching-rule", task_ref="a",
            query="How do Fourier transforms work?")
        self.assertTrue(no_network["external_provider_skipped"])
        self.assertEqual(self.fake.calls, 0)
        with self.assertRaisesRegex(ValueError, "No measured strategy"):
            self.core.reason_auto(domain="no-matching-rule", task_ref="a",
                query="How do Fourier transforms work?", allow_provider=True)
        self.assertEqual(self.fake.calls, 0)

    def test_local_inference_can_receive_source_linked_feedback(self):
        self.learn("routing", TAG_TRAIN)
        output = self.core.reason_local(
            domain="routing", task_ref="verification", query="ORCHID-7 tags B8 W2 P5")
        reported = self.core.feedback(
            receipt_id=output["receipt_id"], expected="BPW",
            evidence_refs=["host:validation-case"], adjustment_hypothesis="Review token priority")
        self.assertTrue(reported["matched"])
        self.assertFalse(reported["correction_added"])
        self.assertEqual(self.core.status()["feedback_receipts"], 1)

    def test_inbox_exposes_native_reasoning_and_calls_no_network(self):
        self.assertIn("reasoning_auto", self.inbox.handlers)
        self.assertIn("reasoning_local", self.inbox.handlers)
        self.assertIn("reasoning_learn_local", self.inbox.handlers)
        self.assertEqual(self.fake.calls, 0)


class FakeHTTP:
    def __init__(self, model):
        self.model = model
        self.calls = []
    def __call__(self, req, timeout=90):
        payload = json.loads(req.data.decode())
        self.calls.append(payload)
        self.last_auth = req.headers.get("Authorization")
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, maximum):
                return json.dumps({
                    "id": "fake-response", "model": payload["model"],
                    "choices": [{"message": {"content": "research answer"}}],
                    "usage": {"prompt_tokens": 1000, "completion_tokens": 100}
                }).encode()
        return Resp()


class CheapProviderTests(unittest.TestCase):
    def test_paid_provider_disabled_by_default(self):
        with patch.dict("os.environ", {
            "BEAN_OPENROUTER_PAID_ENABLED": "0",
            "BEAN_OPENROUTER_PAID_CALL_LIMIT": "0"}):
            with self.assertRaisesRegex(ValueError, "explicit opt-in"):
                OpenRouterProvider(model_name="qwen/qwen3.5-flash-02-23", api_key="fixture")
        with self.assertRaises(ValueError):
            OpenRouterProvider(model_name="expensive/unknown-model", api_key="fixture")

    def test_capped_paid_requests_have_no_hidden_fallback(self):
        with patch.dict("os.environ", {
            "BEAN_OPENROUTER_PAID_ENABLED": "1",
            "BEAN_OPENROUTER_PAID_CALL_LIMIT": "1"}):
            requester = FakeHTTP("qwen/qwen3.5-flash-02-23")
            provider = OpenRouterProvider(
                model_name="qwen/qwen3.5-flash-02-23",
                api_key="fixture-not-live", requester=requester)
            success = provider.complete("Test supported idea", "")
            self.assertTrue(success["ok"])
            self.assertEqual(success["model_name"], "qwen/qwen3.5-flash-02-23")
            self.assertEqual(requester.calls[0]["max_tokens"], 512)
            self.assertAlmostEqual(success["estimated_provider_cost_usd"],
                                   (1000 * .065 + 100 * .26) / 1000000)
            exhausted = provider.complete("Should not hit the network", "")
            self.assertFalse(exhausted["ok"])
            self.assertIn("cap reached", exhausted["error"])
            self.assertEqual(len(requester.calls), 1)
            self.assertEqual(provider.paid_calls_attempted, 1)

    def test_no_automatic_switch_from_free_to_paid(self):
        with patch.dict("os.environ", {"BEAN_OPENROUTER_PAID_ENABLED": "0"}):
            free = OpenRouterProvider(
                model_name="nvidia/nemotron-3-ultra-550b-a55b:free",
                api_key="fixture-not-live")
            self.assertFalse(free.low_cost_paid)
            self.assertEqual(free.paid_calls_attempted, 0)


if __name__ == "__main__":
    unittest.main()

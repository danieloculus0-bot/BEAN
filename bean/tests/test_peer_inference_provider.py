"""Offline synthetic contracts for explicitly selected BEAN peer inference."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

from bean.learning.reasoning_service import _model_response
from bean.reasoning.peer_inference_provider import PeerInferenceProvider
from bean.reasoning.reasoning_engine import adapter_from_name


def node(node_id="a", *, endpoint="https://peer.example/v1/chat/completions",
         model="local-qwen", quote=0.0, latency=100, available=True):
    return {"id": node_id, "endpoint": endpoint, "model": model,
            "quoted_max_cost_usd": quote,
            "advertised_latency_ms": latency, "available": available}


class FakeReply:
    status = 200

    def __init__(self, payload):
        self.data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.data[:limit]


class PeerInferenceTests(unittest.TestCase):
    def provider(self, nodes=None, *, requester=None, budget=0.0, token=None):
        return PeerInferenceProvider(
            nodes or [node()], model_name="local-qwen", enabled=True,
            max_quoted_cost_usd=budget, requester=requester, token=token,
            clock=lambda: 0.25)

    def test_default_remote_disabled_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "disabled"):
                adapter_from_name("peer_inference")
        with self.assertRaisesRegex(ValueError, "opt-in"):
            PeerInferenceProvider([node()], model_name="local-qwen")

    def test_chooses_cheaper_eligible_peer_and_runs_real_adapter_contract(self):
        captured = []

        def fake(request, timeout):
            captured.append((request, timeout))
            return FakeReply({"id": "receipt-7", "model": "local-qwen",
                              "choices": [{"message": {"content": "Evaluated."}}]})

        peers = [node("slow", quote=0.01, latency=200),
                 node("cheap", quote=0.002, latency=120),
                 node("different", model="wrong", quote=0),
                 node("off", quote=0, available=False)]
        provider = self.provider(peers, requester=fake, budget=0.005,
                                 token="fixture-credential")
        result = provider.complete("Analyze task", {"source_ref": "synthetic:1"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider_response_id"], "cheap:receipt-7")
        self.assertEqual(result["peer_receipt"]["quoted_max_cost_usd"], 0.002)
        self.assertFalse(result["verified_outcome"])
        self.assertEqual(len(captured), 1)
        req, timeout = captured[0]
        self.assertEqual(req.full_url, "https://peer.example/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer fixture-credential")
        self.assertEqual(timeout, 30)
        self.assertIn("synthetic:1", json.loads(req.data)["messages"][1]["content"])
        answer, model, kind, receipt = _model_response(provider, "Task", "context")
        self.assertEqual((answer, model, kind, receipt),
                         ("Evaluated.", "local-qwen", "peer_inference", "cheap:receipt-7"))

    def test_without_eligible_bid_no_network_or_auto_cloud_fallback(self):
        calls = []

        def fake(*_args, **_kwargs):
            calls.append(True)
            raise AssertionError("Must not call")

        provider = self.provider([node(quote=0.02)], requester=fake)
        result = provider.complete("Research")
        self.assertFalse(result["ok"])
        self.assertFalse(result["remote_inference"])
        self.assertEqual(calls, [])

    def test_model_alias_mismatch_fails_and_never_retries_other_peer(self):
        calls = []
        def fake(request, timeout):
            calls.append(request.full_url)
            return FakeReply({"id": "x", "model": "unexpected-model",
                              "choices": [{"message": {"content": "No"} }]})
        provider = self.provider([node("a"), node("b", latency=500)], requester=fake)
        result = provider.complete("Test")
        self.assertFalse(result["ok"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["peer_receipt"]["failure_kind"], "ValueError")

    def test_transport_errors_never_emit_secrets_or_provider_bodies(self):
        calls = []
        def broken(request, timeout):
            calls.append(request)
            raise URLError("secret-token-in-provider-error")
        provider = self.provider(requester=broken, token="secret-token")
        result = provider.complete("Sensitive synthetic task")
        self.assertFalse(result["ok"])
        self.assertEqual(len(calls), 1)
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("Sensitive", json.dumps(result))

    def test_bad_configurations_are_rejected(self):
        for endpoint in ("http://peer.example/v1/chat/completions",
                         "https://peer.example/redirect",
                         "https://person:pass@peer.example/v1/chat/completions",
                         "https://peer.example/v1/chat/completions?next=evil"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    self.provider([node(endpoint=endpoint)])
        with self.assertRaises(ValueError):
            self.provider([node("dup"), node("dup")])
        with self.assertRaises(ValueError):
            self.provider([node(quote=float("nan"))])
        with self.assertRaises(ValueError):
            self.provider([node(latency=0)])
        with self.assertRaises(ValueError):
            self.provider([node()], token="bad\ncredential")

    def test_environment_wiring_requires_opt_in_and_explicit_registry(self):
        setting = {"BEAN_PEER_INFERENCE_ENABLED": "1",
                   "BEAN_PEER_MODEL": "local-qwen",
                   "BEAN_PEER_NODES_JSON": json.dumps([node()]),
                   "BEAN_PEER_MAX_QUOTE_USD": "0"}
        with patch.dict(os.environ, setting, clear=True):
            adapter = adapter_from_name("peer_inference")
            self.assertEqual(adapter.adapter_name, "peer_inference")
            self.assertEqual(adapter.eligible_nodes()[0]["id"], "a")
        with patch.dict(os.environ, {"BEAN_PEER_INFERENCE_ENABLED": "1"}, clear=True):
            with self.assertRaises(ValueError):
                adapter_from_name("peer_inference")

    def test_invalid_response_is_not_a_success_receipt(self):
        for body in ({"model": "local-qwen", "id": "test", "choices": []},
                     {"model": "local-qwen", "id": "test",
                      "choices": [{"message": {"content": " "}}]},
                     {"model": "local-qwen", "id": "",
                      "choices": [{"message": {"content": "Answer"}}]}):
            with self.subTest(body=body):
                provider = self.provider(requester=lambda *_a, **_kw: FakeReply(body))
                self.assertFalse(provider.complete("X")["ok"])

    def test_deterministic_tie_break_and_bounded_payload(self):
        provider = self.provider([node("z", latency=100), node("b", latency=100)])
        self.assertEqual([n["id"] for n in provider.eligible_nodes()], ["b", "z"])
        with self.assertRaises(ValueError):
            provider.complete("x" * 12001)
        with self.assertRaises(ValueError):
            provider.complete("x", "y" * 8001)


if __name__ == "__main__":
    unittest.main()

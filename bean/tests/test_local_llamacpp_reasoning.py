"""Prove zero-API local llama.cpp wiring, real HTTP loopback and BEAN persistence.

Fake local server simulates inference protocol, NOT actual model intelligence.
The test cannot establish Qwen reasoning accuracy without installed weights.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from bean.learning import NativeReasoningService
from bean.reasoning.local_llamacpp_provider import (
    LocalLlamaCppProvider, _endpoint,
)
from bean.reasoning.reasoning_engine import adapter_from_name


class _Server(BaseHTTPRequestHandler):
    requests = []
    should_fail = False

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        _Server.requests.append({"path": self.path, "body": body})
        if _Server.should_fail:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"LOCAL_MODEL_LOADING")
            return
        doc = json.loads(body)
        answer = "A locally generated response"
        if "SOURCE RULE" in doc["messages"][-1]["content"]:
            answer = "LOCAL_RULE_APPLIED"
        payload = {"id": "local-completion-1", "model": "bean-local",
                   "choices": [{"message": {"role": "assistant",
                                            "content": answer}}]}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class LocalQwenIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _Server.requests = []
        _Server.should_fail = False
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Server)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        _Server.requests = []
        _Server.should_fail = False
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "bean-memory.sqlite3"
        self.provider = LocalLlamaCppProvider(
            base_url=f"http://127.0.0.1:{self.server.server_port}",
            model_name="bean-local", timeout_seconds=10)
        self.bean = NativeReasoningService(self.path, model=self.provider)
        self.addCleanup(self.bean.close)

    def test_actual_loopback_request_and_no_api_tokens_or_proxy(self):
        with patch.dict("os.environ", {
            "HTTP_PROXY": "http://cloud-proxy.invalid:9999",
            "HTTPS_PROXY": "http://cloud-proxy.invalid:9999",
        }):
            result = self.provider.complete("Explain a calculation", "")
        self.assertTrue(result["ok"])
        self.assertEqual(result["adapter_name"], "local_llamacpp")
        self.assertEqual(result["external_cost_usd"], 0)
        self.assertTrue(result["local_inference"])
        self.assertEqual(len(_Server.requests), 1)
        call = _Server.requests[0]
        self.assertEqual(call["path"], "/v1/chat/completions")
        request = json.loads(call["body"])
        self.assertEqual(request["model"], "bean-local")
        self.assertFalse(request["stream"])
        self.assertLessEqual(request["max_tokens"], 4096)
        self.assertNotIn("api_key", call["body"].decode().lower())
        self.assertNotIn("Authorization", call["body"].decode())

    def test_symbolic_first_then_on_device_language_without_paid_opt_in(self):
        result = self.bean.reason_auto(
            domain="unseen-domain", task_ref="cold-1",
            query="Explain why a measurement varies")
        self.assertEqual(result["answer"], "A locally generated response")
        self.assertEqual(result["provider_kind"], "local_llamacpp")
        self.assertTrue(result["external_provider_skipped"])
        self.assertEqual(result["external_cost_usd"], 0)
        self.assertTrue(result["local_model_invoked"])
        self.assertEqual(result["decision"]["selected_strategy"], "cold")
        self.assertIsNone(result["decision"]["selection_trial_hash"])
        self.assertEqual(self.bean.status()["inference_receipts"], 1)
        self.assertEqual(len(_Server.requests), 1)
        # The answer and model attribution are replayable after restart.
        self.bean.close()
        restored = NativeReasoningService(self.path, model=self.provider)
        try:
            records = [row["data"] for row in restored.bank.journal.events()
                       if row["kind"] == "inference"]
            self.assertEqual(records[0]["purpose"], "local_cold_inference")
            self.assertEqual(records[0]["receipt_id"], result["receipt_id"])
            self.assertEqual(records[0]["provider_kind"], "local_llamacpp")
            outcome = restored.feedback(
                receipt_id=result["receipt_id"],
                expected="A locally generated response",
                evidence_refs=["host:independent-check"])
            self.assertTrue(outcome["matched"])
            self.assertEqual(restored.status()["feedback_receipts"], 1)
        finally:
            restored.close()

    def test_measured_BEAN_lesson_reaches_real_local_model(self):
        self.bean.reflect(
            domain="inspection", task_id="dev",
            observed="uncertain", expected="SOURCE RULE",
            adjustment_hypothesis="SOURCE RULE compare to reference",
            evidence_refs=["fixture:training"])
        self.bean.retain_skill(
            domain="inspection", name="special rule",
            steps=["SOURCE RULE"], passed=True,
            evidence_refs=["fixture:skill"])
        self.bean.propose_instruction(
            domain="inspection", instruction="SOURCE RULE",
            evidence_refs=["fixture:prompt"])
        self.bean.reflect(
            domain="other", task_id="placebo",
            observed="wrong", expected="right",
            adjustment_hypothesis="unrelated planet data",
            evidence_refs=["fixture:placebo"])
        rows = [
            {"task_id": t, "arm": arm, "replicate": 0,
             "passed": arm == "reflection", "evidence_ref": f"{t}:{arm}"}
            for t in ("dev-a", "dev-b")
            for arm in ("cold", "placebo", "reflection", "skill", "prompt")
        ]
        chosen = self.bean.choose_from_outcomes(
            domain="inspection", rows=rows, evaluator_id="fixture",
            dataset_id="development-only-fixture")
        self.assertEqual(chosen["arm"], "reflection")
        reply = self.bean.reason_auto(
            domain="inspection", task_ref="unseen",
            query="Please compare this reference reading on an unfamiliar new sample")
        self.assertEqual(reply["answer"], "LOCAL_RULE_APPLIED")
        self.assertEqual(reply["decision"]["selected_strategy"], "reflection")
        self.assertEqual(reply["provider_kind"], "local_llamacpp")
        self.assertTrue(reply["external_provider_skipped"])
        self.assertIn("SOURCE RULE",
                      json.loads(_Server.requests[-1]["body"])["messages"][-1]["content"])

    def test_503_cannot_ever_trigger_cloud_fallback_or_fake_success(self):
        _Server.should_fail = True
        answer = self.bean.reason_auto(
            domain="new", task_ref="offline",
            query="How should BEAN solve this unknown question?")
        self.assertEqual(answer["status"], "local_model_unavailable")
        self.assertEqual(answer["external_cost_usd"], 0)
        self.assertEqual(answer["external_provider_skipped"], True)
        self.assertEqual(self.bean.status()["failed_inference_attempts"], 1)
        attempts = [x["data"] for x in self.bean.bank.journal.events()
                    if x["kind"] == "inference"]
        self.assertEqual(attempts[0]["answer"], "")
        self.assertEqual(attempts[0]["status"], "failed")
        self.assertEqual(len(_Server.requests), 1)

    def test_external_names_cannot_be_used_as_local_endpoints(self):
        for url in (
            "https://127.0.0.1:8080", "http://10.1.1.1:8080",
            "http://localhost:8080", "http://cloud.host.com:8080",
            "http://user:pass@127.0.0.1:8080", "http://127.0.0.1:8080/evil",
            "http://127.0.0.1:8080?redirect=https://cloud.io",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _endpoint(url)
        with self.assertRaises(ValueError):
            LocalLlamaCppProvider(model_name="alias with spaces")
        self.assertEqual(adapter_from_name("llamacpp").adapter_name,
                         "local_llamacpp")


if __name__ == "__main__":
    unittest.main()

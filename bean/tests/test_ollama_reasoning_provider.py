"""Offline contract tests for the opt-in local Ollama reasoning path."""
from __future__ import annotations

import json

import pytest

from bean.integration import BeanReasoningLayer
from bean.reasoning.ollama_provider import OllamaProvider
from bean.reasoning.reasoning_engine import adapter_from_name
from bean.reasoning.prompt_builder import OLLAMA_RESPONSE_SCHEMA, build_ollama_prompt
from bean.voice.ollama import OllamaClient


REPLY = json.dumps({
    "summary": "Validate the next coding change against held-out tests.",
    "observations": ["A local experiment was requested."],
    "interpretations": [],
    "assumptions": [],
    "uncertainties": ["Success has not been verified."],
    "evidence_refs": [],
    "candidate_steps": ["Run tests in an isolated workspace."],
    "risk_flags": [],
    "confidence": 0.55,
})


class FakeClient:
    def __init__(self, reply=REPLY, failure=None):
        self.reply = reply
        self.failure = failure
        self.calls = []

    def chat_json(self, model, messages, schema=None):
        self.calls.append((model, messages, schema))
        if self.failure is not None:
            raise self.failure
        return self.reply


def test_ollama_is_explicitly_selectable(monkeypatch):
    monkeypatch.setenv("BEAN_OLLAMA_MODEL", "qwen2.5-coder:1.5b")
    provider = adapter_from_name("ollama")
    assert provider.adapter_name == "ollama"
    assert provider.model_name == "qwen2.5-coder:1.5b"
    assert adapter_from_name("mock").adapter_name == "mock"


def test_provider_calls_local_json_transport_and_reports_receipt():
    client = FakeClient()
    provider = OllamaProvider(client=client)
    result = provider.complete("reason about this observation")
    assert result["ok"] is True
    assert result["adapter_name"] == "ollama"
    assert result["model_name"] == "qwen2.5-coder:1.5b"
    assert json.loads(result["raw_text"])["confidence"] == 0.55
    assert client.calls == [("qwen2.5-coder:1.5b", [
        {"role": "user", "content": "reason about this observation"}
    ], OLLAMA_RESPONSE_SCHEMA)]


def test_provider_refuses_remote_endpoints(monkeypatch):
    monkeypatch.setenv("BEAN_OLLAMA_URL", "https://example.com")
    with pytest.raises(ValueError, match="local Ollama"):
        OllamaProvider()


def test_structured_ollama_call_uses_json_mode():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, *_):
            return json.dumps({"message": {"content": REPLY}}).encode("utf-8")

    calls = []

    def opener(req, timeout):
        calls.append(req)
        return FakeResponse()

    reply = OllamaClient(opener=opener).chat_json(
        "qwen2.5-coder:1.5b", [{"role": "user", "content": "test"}],
        schema=OLLAMA_RESPONSE_SCHEMA,
    )
    assert reply == REPLY
    assert calls[0].full_url == "http://127.0.0.1:11434/api/chat"
    data = json.loads(calls[0].data)
    assert data["format"] == OLLAMA_RESPONSE_SCHEMA
    assert data["options"]["num_predict"] == 512
    assert data["stream"] is False


def test_ollama_reasoning_persists_proposal_without_execution(tmp_path):
    db_path = tmp_path / "bean_ollama.sqlite"
    with BeanReasoningLayer(str(db_path), adapter=OllamaProvider(client=FakeClient())) as bean:
        receipt = bean.observe_and_reason(
            "Operator requested a local inference check.",
            data={"source": "offline_test"},
            adapter_name="ollama",
        )
        assert receipt["proposal_id"]
        assert receipt["requires_supervisor_review"] is True
        assert receipt["motion_command_generated"] is False
        assert receipt["memory_written"] is False
        row = bean.store.fetchone(
            "SELECT summary, risk_flags_json, status FROM reasoning_proposals WHERE proposal_id=?",
            (receipt["proposal_id"],),
        )
        assert row["summary"] == "Validate the next coding change against held-out tests."
        assert row["status"] == "pending_review"
        assert json.loads(row["risk_flags_json"]) == []
        req = bean.store.fetchone(
            "SELECT adapter_name, model_name FROM reasoning_requests WHERE request_id=?",
            (receipt["request_id"],),
        )
        assert req["adapter_name"] == "ollama"
        assert req["model_name"] == "qwen2.5-coder:1.5b"


def test_unavailable_ollama_is_recorded_as_unavailable(tmp_path):
    client = FakeClient(failure=ConnectionError("server is unavailable"))
    with BeanReasoningLayer(
        str(tmp_path / "unavailable.sqlite"), adapter=OllamaProvider(client=client)
    ) as bean:
        receipt = bean.observe_and_reason("Test a disconnected local model.", adapter_name="ollama")
        row = bean.store.fetchone(
            "SELECT summary, risk_flags_json, status, confidence FROM reasoning_proposals WHERE proposal_id=?",
            (receipt["proposal_id"],),
        )
        assert row["summary"] == "provider unavailable"
        assert "provider_unavailable" in json.loads(row["risk_flags_json"])
        assert row["confidence"] == 0.0
        assert row["status"] == "pending_review"
        assert receipt["motion_command_generated"] is False


def test_model_repetition_and_truncated_json_are_fail_closed(tmp_path):
    # Regression for an actual Windows Ollama 1.5B output: endless identity
    # repetition produced an unterminated summary string.
    repeated = '{"summary": "' + ("BEAN is a persistent reasoning system. " * 100)
    with BeanReasoningLayer(
        str(tmp_path / "looped.sqlite"), adapter=OllamaProvider(client=FakeClient(reply=repeated))
    ) as bean:
        receipt = bean.observe_and_reason(
            "Operator requested a local inference check.", adapter_name="ollama",
        )
        assert receipt["structured_response_valid"] is False
        assert receipt["filter_passed"] is False
        assert receipt["motion_command_generated"] is False
        response = bean.store.fetchone(
            "SELECT raw_text, parse_success FROM reasoning_responses WHERE response_id=?",
            (receipt["response_id"],),
        )
        assert response["raw_text"] == repeated  # forensic evidence retained
        assert not response["parse_success"]
        proposal = bean.store.fetchone(
            "SELECT risk_flags_json, confidence, status FROM reasoning_proposals WHERE proposal_id=?",
            (receipt["proposal_id"],),
        )
        assert "parse_failed" in json.loads(proposal["risk_flags_json"])
        assert proposal["confidence"] == 0.0
        assert proposal["status"] == "pending_review"


def test_json_missing_required_keys_fails_closed(tmp_path):
    with BeanReasoningLayer(
        str(tmp_path / "partial.sqlite"),
        adapter=OllamaProvider(client=FakeClient(reply='{"summary":"Some plausible text"}')),
    ) as bean:
        receipt = bean.observe_and_reason("Incomplete JSON test", adapter_name="ollama")
        assert receipt["structured_response_valid"] is False
        assert receipt["filter_passed"] is False
        row = bean.store.fetchone(
            "SELECT risk_flags_json FROM reasoning_proposals WHERE proposal_id=?",
            (receipt["proposal_id"],),
        )
        assert "parse_failed" in json.loads(row["risk_flags_json"])


def test_compact_ollama_prompt_avoids_repetitive_identity_context():
    context = {
        "session": {"source_event_id": 17},
        "identity": {"what_bean_is": "BEAN is " * 1000},
        "recent_events": [{"id": 17, "summary": "The model returned incomplete JSON.", "source": "system"}],
        "active_boundaries": [],
    }
    prompt = build_ollama_prompt(context, "analysis")
    assert '"source_event_id":17' in prompt
    assert "The model returned incomplete JSON." in prompt
    assert "BEAN is BEAN is" not in prompt
    assert len(prompt) < 1500


def test_oversized_ollama_json_is_rejected_not_silently_truncated():
    from bean.voice.ollama import OllamaError

    client = OllamaClient()
    client._json = lambda *_: {"message": {"content": '{"summary":"' + "a" * 20001}}
    with pytest.raises(OllamaError, match="size limit"):
        client.chat_json("qwen2.5-coder:1.5b", [{"role": "user", "content": "test"}])

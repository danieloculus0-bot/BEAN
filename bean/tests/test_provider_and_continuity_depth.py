"""Offline provider, response-integrity, and boot-continuity regression tests."""
import io
import json
import urllib.error

import pytest


def test_openai_provider_reports_missing_credentials_without_network(monkeypatch):
    from bean.reasoning.openai_provider import OpenAIProvider
    import bean.reasoning.openai_provider as module
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    def no_network(*args, **kwargs):
        raise AssertionError("Provider attempted a network call without credentials")
    monkeypatch.setattr(module.urllib.request, "urlopen", no_network)
    response = OpenAIProvider(api_key=None).complete("synthetic test")
    assert response["ok"] is False
    assert "not set" in response["error"]


def test_openai_provider_extracts_structured_text_without_live_api(monkeypatch):
    from bean.reasoning.openai_provider import OpenAIProvider
    import bean.reasoning.openai_provider as module

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"id": "fake_id", "output": [{"content": [{"type": "output_text", "text": '{"summary": "evidence only"}'}]}]}).encode()

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/v1/responses")
        assert request.get_header("Authorization") == "Bearer fake-test-key"
        assert json.loads(request.data)["tool_choice"] == "none"
        return FakeResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    response = OpenAIProvider(api_key="fake-test-key").complete("test prompt")
    assert response["ok"] is True
    assert response["provider_response_id"] == "fake_id"
    assert json.loads(response["raw_text"])["summary"] == "evidence only"


def test_openai_provider_fails_closed_on_http_error(monkeypatch):
    from bean.reasoning.openai_provider import OpenAIProvider
    import bean.reasoning.openai_provider as module
    def fake_http_error(*args, **kwargs):
        raise urllib.error.HTTPError("https://fake.invalid", 429, "rate limited", {}, io.BytesIO(b"rate limited"))
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_http_error)
    response = OpenAIProvider(api_key="fake-test-key").complete("test prompt")
    assert response["ok"] is False
    assert "429" in response["error"]


@pytest.mark.parametrize("confidence", ['"NaN"', '"Infinity"', '"bad"', 'null'])
def test_reasoning_parser_rejects_invalid_confidence(confidence):
    from bean.reasoning.response_parser import parse_response
    result = parse_response('{"summary":"test","confidence":' + confidence + '}')
    assert result["parse_success"] is False
    assert result["confidence"] == 0.0


@pytest.mark.parametrize("confidence,expected", [('-2', 0.0), ('2', 1.0), ('0.45', 0.45)])
def test_reasoning_parser_bounds_valid_confidence(confidence, expected):
    from bean.reasoning.response_parser import parse_response
    result = parse_response('{"summary":"test","confidence":' + confidence + '}')
    assert result["parse_success"] is True
    assert result["confidence"] == expected


def test_bootstrap_two_sessions_preserves_identity_and_shutdown(tmp_path, monkeypatch):
    import bean.runtime.bootstrap as runtime
    from bean.memory.store import _local, get_store
    from bean.memory.session import get_session
    monkeypatch.setattr(runtime.atexit, "register", lambda *args: None)
    monkeypatch.setattr(runtime.signal, "signal", lambda *args: None)
    if getattr(_local, "conn", None):
        _local.conn.close()
        _local.conn = None
    db = str(tmp_path / "continuity.db")
    try:
        first = runtime.start_bean(db_path=db, silent=True)
        assert first["identity"]["developmental_stage"] == "brain-first-bootable-0.13"
        runtime.shutdown_bean(first)
        runtime.shutdown_bean(first)
        assert get_session(first["session_uuid"])["shutdown_reason"] == "clean"
        second = runtime.start_bean(db_path=db, silent=True)
        assert second["continuity"]["total_boots"] == 2
        assert second["continuity"]["recent_sessions"][1]["session_uuid"] == first["session_uuid"]
        assert second["continuity"]["recent_sessions"][1]["shutdown_reason"] == "clean"
        runtime.shutdown_bean(second)
        assert get_store().fetchone("SELECT COUNT(*) AS n FROM sessions")["n"] == 2
    finally:
        if getattr(_local, "conn", None):
            _local.conn.close()
            _local.conn = None
        runtime._active_ctx = None

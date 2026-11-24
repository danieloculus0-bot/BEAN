"""Synthetic HTTP mechanism tests, never proof of live BEAN artwork.

Mock replies and any resulting previews stay in pytest's temporary directory.
The configured model names explicitly identify this synthetic unit-test data.
"""
from base64 import b64decode
import json
from pathlib import Path

import pytest

from bean.creativity.artifacts import file_hash
from bean.creativity.sketch_lab import execution_mode
from bean.learning import NativeReasoningService
from bean.reasoning.ollama_provider import OllamaProvider
from bean.reasoning.prompt_builder import OLLAMA_RESPONSE_SCHEMA
from bean.runtime.orchestration_domains import register_domain_tools
from bean.tests.test_sketch_lab import FakeModel, drawing
from bean.voice.ollama import OllamaClient, OllamaError


ARTIST = "synthetic-unit-test-artist"
VISION = "synthetic-unit-test-vision"
SUBJECT = "synthetic unit-test object"


class RegisteredTools:
    def __init__(self, core, root):
        self.core, self.tools = core, {}
        register_domain_tools(self, body_state=None, motion_safety=None,
                              simulator=None, model_store=None, artifact_root=root)

    def register(self, name, description, handler):
        self.tools[name] = handler


def synthetic_http(monkeypatch):
    calls = []

    def respond(client, route, body=None):
        calls.append((client, route, body))
        if route == "/api/tags":
            return {"models": [{"name": ARTIST, "digest": "a" * 64},
                               {"name": VISION, "digest": "b" * 64}]}
        if route == "/api/show":
            return {"capabilities": ["completion", "vision"]}
        assert route == "/api/chat"
        props = body["format"]["properties"]
        if "recognized_subject" in props:
            answer = {"recognized_subject": SUBJECT,
                      "observations": "Synthetic HTTP test observation",
                      "feedback": "Synthetic HTTP test feedback: improve separation",
                      "scores": {"spatial_coherence": 3, "subject_recognition": 3,
                                 "composition": 3}}
        elif "subject" in props:
            answer = {"subject": SUBJECT, "reference_query": ""}
        elif "intent" in props:
            answer = {"intent": "Synthetic test drawing plan",
                      "components": ["test marks"], "composition": "synthetic fixture",
                      "revision_reason": "Exercise retained feedback only"}
        elif "shapes" in props:
            answer = json.loads(drawing())
        elif "claimed_subject" in props:
            answer = {"claimed_subject": SUBJECT, "changes": "Synthetic critique",
                      "satisfied": True}
        elif "selected_attempt" in props:
            answer = {"selected_attempt": 2, "reason": "Synthetic test selection"}
        else:
            assert body["format"] == OLLAMA_RESPONSE_SCHEMA
            answer = {"summary": "Synthetic analytical response", "observations": [],
                      "interpretations": [], "assumptions": [], "uncertainties": [],
                      "evidence_refs": [], "candidate_steps": [], "risk_flags": [],
                      "confidence": 0}
        return {"message": {"content": json.dumps(answer)}}

    monkeypatch.setattr(OllamaClient, "_json", respond)
    return calls


@pytest.mark.parametrize("reviewer", [None, VISION, "missing-synthetic-unit-test-vision"])
def test_core_ollama_draw_uses_scoped_adapter_retains_attempts_and_reopens(
        tmp_path, monkeypatch, reviewer):
    pytest.importorskip("cairosvg")
    pytest.importorskip("PIL.Image")
    if reviewer:
        monkeypatch.setenv("BEAN_DRAW_VISION_MODEL", reviewer)
    else:
        monkeypatch.delenv("BEAN_DRAW_VISION_MODEL", raising=False)
    calls = synthetic_http(monkeypatch)
    db = tmp_path / "private-test-core.sqlite3"
    original = OllamaProvider(model_name=ARTIST)
    client = original.client
    assert execution_mode(original) == "unverified"
    core = NativeReasoningService(db, model=original)
    bank, journal = core.bank, core.bank.journal
    try:
        result = RegisteredTools(core, tmp_path).tools["draw"]({}, "first")
        assert result["status"] == "success" and result["attempts"] == 2
        assert result["visual_review_requested"] == bool(reviewer)
        assert result["visual_success_independently_verified"] is False
        assert core.model is original and original.client is client
        assert core.bank is bank and core.bank.journal is journal
        manifest = json.loads(Path(result["receipt"]).read_text())
        assert manifest["model_digest"] == "a" * 64
        assert manifest["model_id"] == ARTIST
        assert manifest["execution_mode"] == "live_model"  # HTTP is mocked in this test only.
        assert manifest["subject_source"] == "autonomous"
        for attempt in result["artifacts"]:
            row = json.loads(Path(attempt["metadata"]).read_text())
            assert file_hash(attempt["svg"]) == row["svg_sha256"]
            assert file_hash(attempt["png"]) == row["png_sha256"]
            feedback = row["external_feedback"]
            if reviewer == VISION:
                assert feedback["state"] == "host_reported_pixel_review"
                assert feedback["model_id"] == VISION
                evidence = json.loads((Path(result["receipt"]).parent /
                                      feedback["review_file"]).read_text())
                assert evidence["evaluation_protocol"] == "blind_then_targeted_min_v1"
            else:
                assert feedback["state"] == "unavailable"
                assert "scores" not in feedback
        assert all(c is client for c, _, _ in calls)
        artist_calls = [body for _, route, body in calls
                        if route == "/api/chat" and body["model"] == ARTIST]
        assert any("shapes" in b["format"]["properties"] for b in artist_calls)
        assert all(b["format"] != OLLAMA_RESPONSE_SCHEMA for b in artist_calls)
        if reviewer == VISION:
            image_calls = [body for _, route, body in calls
                           if route == "/api/chat" and body["model"] == VISION]
            assert len(image_calls) == 4
            png_bytes = {Path(a["png"]).read_bytes() for a in result["artifacts"]}
            assert all(b64decode(b["messages"][0]["images"][0]) in png_bytes
                       for b in image_calls)
            draw_calls = [b for b in artist_calls if "shapes" in b["format"]["properties"]]
            assert "Synthetic HTTP test feedback" in draw_calls[1]["messages"][0]["content"]
        # The same ordinary provider still sends its original analytical schema.
        assert original.complete("Synthetic ordinary reasoning check")["ok"] is True
        assert calls[-1][2]["format"] == OLLAMA_RESPONSE_SCHEMA
        journal.verify()
    finally:
        core.close()

    reopened = NativeReasoningService(db, model=original)
    try:
        rows = [e["data"] for e in reopened.bank.journal.events()
                if e["kind"] == "trial" and e["data"].get("experiment") == "bean_sketch_v1"]
        assert len(rows) == 2
        assert all(row["subject"] == SUBJECT for row in rows)
        second = RegisteredTools(reopened, tmp_path).tools["draw"]({}, "after-reopen")
        memory = json.loads(Path(second["receipt"]).read_text())["memory_context_records"]
        assert {r["subject"] for r in memory} == {SUBJECT}
        assert len(memory) == 2
        saved = [e["data"] for e in reopened.bank.journal.events()
                 if e["kind"] == "trial" and e["data"].get("experiment") == "bean_sketch_v1"]
        assert len(saved) == 4
        assert reopened.model is original
        reopened.bank.journal.verify()
    finally:
        reopened.close()


@pytest.mark.parametrize("kind", ["injected_transport", "subclass", "fixture", "missing"])
def test_draw_keeps_live_guards_and_failure_receipts(tmp_path, monkeypatch, kind):
    monkeypatch.delenv("BEAN_DRAW_VISION_MODEL", raising=False)
    if kind == "injected_transport":
        client = OllamaClient(opener=lambda *a, **kw: pytest.fail("Must not call injected HTTP"))
        model = OllamaProvider(model_name=ARTIST, client=client)
    elif kind == "subclass":
        class SyntheticSubclass(OllamaProvider):
            def complete(self, *args, **kwargs):
                pytest.fail("Must not call scripted subclass")
        model = SyntheticSubclass(model_name=ARTIST)
    elif kind == "fixture":
        model = FakeModel([])
    else:
        model = None
    core = NativeReasoningService(tmp_path / "test.sqlite3", model=model)
    try:
        with pytest.raises(ValueError, match="Live run requires|No reasoning model"):
            RegisteredTools(core, tmp_path).tools["draw"]({}, "rejected")
        out = tmp_path / "draw" / "rejected"
        receipt = json.loads((out / "run.json").read_text())
        assert receipt["state"] == "run_failed" and receipt["attempts"] == 0
        assert receipt["execution_mode"] != "live_model"
        assert receipt["journal_tip"]
        assert core.model is model
        assert not list(out.glob("*.svg")) and not list(out.glob("*.png"))
        core.bank.journal.verify()
    finally:
        core.close()


def test_unavailable_real_transport_does_not_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("BEAN_DRAW_VISION_MODEL", raising=False)
    def unavailable(*args, **kwargs):
        raise OllamaError("Synthetic HTTP fixture: provider unavailable")
    monkeypatch.setattr(OllamaClient, "_json", unavailable)
    original = OllamaProvider(model_name=ARTIST)
    core = NativeReasoningService(tmp_path / "test.sqlite3", model=original)
    try:
        with pytest.raises(OllamaError, match="provider unavailable"):
            RegisteredTools(core, tmp_path).tools["draw"]({}, "unavailable")
        receipt = json.loads((tmp_path / "draw/unavailable/run.json").read_text())
        assert receipt["state"] == "run_failed" and receipt["attempts"] == 0
        assert core.model is original
        assert not list((tmp_path / "draw/unavailable").glob("*.png"))
    finally:
        core.close()

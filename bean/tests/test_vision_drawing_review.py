"""Synthetic transport contracts; never evidence of genuine vision or artwork.

These tests patch the existing transport methods to inspect actual PNG payloads.
Published/live drawing runs must use the unpatched local provider and retain
its own receipts. Optional image dependencies are required only by pixel tests.
"""
from base64 import b64decode
import json
from pathlib import Path
import subprocess

import pytest

from bean.creativity.artifacts import (
    OllamaVisionReviewer, file_hash, validate_feedback,
)
from bean.creativity.drawing_benchmark import execute, protocol
from bean.creativity.sketch_lab import SketchLab, draw_svg
from bean.learning import NativeReasoningService
from bean.tests.test_sketch_lab import FakeModel, drawing, review
from bean.voice.ollama import OllamaClient


@pytest.fixture
def pixel_preview(tmp_path):
    try:
        import cairosvg  # noqa: F401 - real local pixels required by these tests
        from PIL import Image  # noqa: F401
    except (ImportError, OSError) as exc:
        pytest.skip("Optional PNG renderer unavailable: " + str(exc))
    from bean.creativity.artifacts import rasterize
    svg = tmp_path / "synthetic-transport.svg"
    png = svg.with_suffix(".png")
    draw_svg([{"type": "line", "x1": 20, "y1": 30, "x2": 210, "y2": 190}],
             svg, "stdlib")
    rasterize(svg, png)
    return png


def install_synthetic_vision_transport(monkeypatch, *, reply=None,
                                       available=True, vision=True):
    """Explicit synthetic transport that records the image-bearing request."""
    calls = []
    outcome = reply if reply is not None else {
        "recognized_subject": "Unconnected lines; intended subject unclear",
        "observations": "A black diagonal mark on a white canvas",
        "feedback": "The visible outline does not make the requested object recognizable.",
        "scores": {"spatial_coherence": 1, "subject_recognition": 0, "composition": 1},
    }

    def fake_json(self, route, body=None):
        calls.append((route, body))
        if route == "/api/tags":
            return {"models": ([{"name": "synthetic-vision-fixture", "digest": "b" * 64}]
                               if available else [])}
        if route == "/api/show":
            return {"capabilities": ["completion", "vision"] if vision else ["completion"]}
        raise AssertionError("Unexpected synthetic test route: " + route)

    def fake_chat(self, model, messages, **kwargs):
        calls.append(("chat_json", {"model": model, "messages": messages, **kwargs}))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome if isinstance(outcome, str) else json.dumps(outcome)

    monkeypatch.setattr(OllamaClient, "_json", fake_json)
    monkeypatch.setattr(OllamaClient, "chat_json", fake_chat)
    return calls


def test_actual_png_bytes_sent_and_review_identity_retained(pixel_preview, monkeypatch):
    calls = install_synthetic_vision_transport(monkeypatch)
    evaluator = OllamaVisionReviewer("synthetic-vision-fixture")
    result = evaluator(pixel_preview, "a synthetic test object")
    sent = next(body for route, body in calls if route == "chat_json")
    assert sent["model"] == "synthetic-vision-fixture"
    assert b64decode(sent["messages"][0]["images"][0]) == pixel_preview.read_bytes()
    assert "ATTACHED IMAGE" in sent["messages"][0]["content"]
    assert sent["schema"]["properties"]["scores"]["required"]
    assert result["kind"] == "vision_model"
    assert result["satisfactory"] is False
    assert result["independently_authenticated"] is False
    assert result["image_sha256"] == file_hash(pixel_preview)
    assert result["provider_kind"] == "ollama"
    assert result["model_id"] == "synthetic-vision-fixture"
    assert result["model_digest"] == "b" * 64
    assert result["recognized_subject"].startswith("Unconnected lines")
    assert result["observations"] == "A black diagonal mark on a white canvas"
    receipt = pixel_preview.with_suffix(".vision.json")
    assert result["review_file"] == receipt.name
    assert result["review_sha256"] == file_hash(receipt)
    retained = json.loads(receipt.read_text())
    assert retained["state"] == "model_reported_pixel_review"
    assert retained["image_sha256"] == result["image_sha256"]
    assert json.loads(retained["raw_response"])["scores"] == result["scores"]
    assert validate_feedback(result, pixel_preview)["model_digest"] == "b" * 64


@pytest.mark.parametrize("available,vision,reason", [
    (False, True, "not installed"),
    (True, False, "image capability"),
])
def test_unavailable_or_text_only_provider_cannot_claim_vision(
        pixel_preview, monkeypatch, available, vision, reason):
    calls = install_synthetic_vision_transport(monkeypatch, available=available, vision=vision)
    report = OllamaVisionReviewer("synthetic-vision-fixture")(pixel_preview, "test object")
    assert report["state"] == "unavailable"
    assert reason in report["reason"]
    assert not any(route == "chat_json" for route, _ in calls)
    receipt = json.loads(pixel_preview.with_suffix(".vision.json").read_text())
    assert receipt["state"] == "unavailable"
    assert receipt["image_sha256"] == file_hash(pixel_preview)
    assert "report" not in receipt


@pytest.mark.parametrize("response", [
    "not JSON",
    "[]",
    {"recognized_subject": "unclear", "observations": "lines", "feedback": "Unclear shape.",
     "scores": {"spatial_coherence": 1, "subject_recognition": 0}},
    {"recognized_subject": "unclear", "observations": "lines", "feedback": "Unclear shape.",
     "scores": {"spatial_coherence": 1, "subject_recognition": 5, "composition": 1}},
    {"recognized_subject": "unclear", "observations": "lines", "feedback": "Unclear shape.",
     "scores": {"spatial_coherence": True, "subject_recognition": 0, "composition": 1}},
    RuntimeError("synthetic provider unreachable"),
])
def test_bad_or_failed_provider_report_is_preserved_as_unavailable(
        pixel_preview, monkeypatch, response):
    install_synthetic_vision_transport(monkeypatch, reply=response)
    result = OllamaVisionReviewer("synthetic-vision-fixture")(pixel_preview, "test object")
    assert result["state"] == "unavailable"
    assert result.get("satisfactory") is not True
    receipt = json.loads(pixel_preview.with_suffix(".vision.json").read_text())
    assert receipt["state"] == "unavailable" and receipt["error"]
    assert "report" not in receipt
    if not isinstance(response, Exception):
        assert "raw_response" in receipt


def test_injected_transport_cannot_be_counted_as_live_review(pixel_preview):
    class SyntheticTransport:
        def _json(self, *args, **kwargs):
            raise AssertionError("Rejected transport must not be called")
        def chat_json(self, *args, **kwargs):
            raise AssertionError("Rejected transport must not be called")
    report = OllamaVisionReviewer("synthetic-vision-fixture", client=SyntheticTransport())(
        pixel_preview, "test object")
    assert report["state"] == "unavailable"
    assert "Injected vision transport" in report["reason"]
    assert json.loads(pixel_preview.with_suffix(".vision.json").read_text())["state"] == "unavailable"


def test_model_satisfaction_is_derived_from_all_three_scores(pixel_preview, monkeypatch):
    install_synthetic_vision_transport(monkeypatch, reply={
        "recognized_subject": "a synthetic object", "observations": "Test response only",
        "feedback": "Synthetic rating contract, not a genuine visual observation.",
        "satisfactory": False,
        "scores": {"spatial_coherence": 3, "subject_recognition": 4, "composition": 3},
    })
    report = OllamaVisionReviewer("synthetic-vision-fixture")(pixel_preview, "test object")
    assert report["satisfactory"] is True
    assert report["independently_authenticated"] is False


def test_real_pixel_review_feedback_reaches_next_drawing_prompt(tmp_path, pixel_preview, monkeypatch):
    install_synthetic_vision_transport(monkeypatch)
    model = FakeModel([drawing(), review(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.sqlite3", model=model)
    try:
        result = SketchLab(core, visual_judge=OllamaVisionReviewer("synthetic-vision-fixture")).run(
            task_ref="synthetic-vision-revision", output_dir=tmp_path / "attempts",
            subject="a synthetic test object", max_attempts=2,
            complete_all_attempts=True, backend="stdlib")
        assert result["attempts"] == 2
        assert "does not make the requested object recognizable" in model.requests[2]
        assert "synthetic-vision-fixture" in model.requests[2]
        for attempt in (1, 2):
            row = json.loads((tmp_path / "attempts" / ("attempt_%02d.json" % attempt)).read_text())
            assert row["execution_mode"] == "synthetic_fixture"
            assert row["external_feedback"]["model_digest"] == "b" * 64
            raw = tmp_path / "attempts" / row["external_feedback"]["review_file"]
            assert file_hash(raw) == row["external_feedback"]["review_sha256"]
            assert row["independent_visual_verification"] is False
    finally:
        core.close()


def test_automatic_vision_model_forwarded_to_every_matched_process(tmp_path):
    commands = []
    def unavailable(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 2, "", "synthetic unavailable test")
    result = execute(protocol(["a teapot"], ["a sailboat"], attempts=2),
                     tmp_path / "benchmark", vision_model="synthetic-vision-fixture",
                     runner=unavailable)
    assert len(commands) == 4
    assert all(command[command.index("--vision-model") + 1] == "synthetic-vision-fixture"
               for command in commands)
    assert all("--require-live" in command for command in commands)
    assert result["learning_improvement_verified"] is False
    assert all(row["process_returncode"] == 2 for row in result["outcomes"])

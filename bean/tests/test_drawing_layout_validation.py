"""Synthetic layout regressions, never evidence that a live model can draw."""
import json
from pathlib import Path

import pytest

from bean.creativity.artifacts import file_hash
from bean.creativity.sketch_lab import SketchLab, drawing_schema, validate_shapes
from bean.learning import NativeReasoningService
from bean.tests.test_sketch_lab import FakeModel, drawing, review


def test_drawing_schema_uses_numeric_ranges_without_coordinate_enumerations():
    schema = drawing_schema()
    variants = schema["properties"]["shapes"]["items"]["anyOf"]
    for variant in variants:
        for name, definition in variant["properties"].items():
            if name == "type":
                continue
            if name == "points":
                definition = definition["items"]["items"]
            assert definition["type"] == "integer"
            assert definition["minimum"] == (1 if name in ("r", "w", "h") else 0)
            assert definition["maximum"] == 256
            assert "enum" not in definition


@pytest.mark.parametrize("shape", [
    {"type": "circle", "cx": 20, "cy": 128, "r": 21},
    {"type": "circle", "cx": 240, "cy": 128, "r": 20},
    {"type": "circle", "cx": 128, "cy": 240, "r": 20},
    {"type": "rect", "x": 240, "y": 10, "w": 20, "h": 10},
    {"type": "rect", "x": 70, "y": 240, "w": 96, "h": 30},
])
def test_shape_extents_cannot_silently_clip_beyond_the_canvas(shape):
    with pytest.raises(ValueError, match="primitive 0 .* extends outside 0..256"):
        validate_shapes([shape])


def test_visible_shapes_may_reach_the_canvas_boundary():
    shapes = [
        {"type": "circle", "cx": 128, "cy": 128, "r": 128},
        {"type": "rect", "x": 240, "y": 240, "w": 16, "h": 16},
        {"type": "line", "x1": 0, "y1": 0, "x2": 256, "y2": 256},
    ]
    assert validate_shapes(shapes) == shapes


def test_clipped_geometry_failure_is_retained_and_reaches_the_next_attempt(tmp_path):
    invalid = json.dumps({"description": "Synthetic clipped rectangle", "shapes": [
        {"type": "rect", "x": 70, "y": 240, "w": 96, "h": 30}]})
    model = FakeModel([invalid, drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.sqlite3", model=model)
    out = tmp_path / "out"
    try:
        result = SketchLab(core).run(
            task_ref="synthetic-layout-revision", output_dir=out,
            subject="synthetic subject", max_attempts=2, backend="stdlib")
        assert result["attempts"] == 2
        failed = json.loads((out / "attempt_01.json").read_text())
        assert failed["status"] == "attempt_failed_ValueError"
        assert "(70, 240, 166, 270)" in failed["error"]
        assert failed["svg_file"] is None and failed["png_file"] is None
        raw_path = out / failed["raw_file"]
        assert file_hash(raw_path) == failed["raw_sha256"]
        assert json.loads(raw_path.read_text())[0]["response"] == invalid
        assert failed["error"] in model.requests[1]
        assert "Synthetic clipped rectangle" in model.requests[1]
        trials = [event["data"] for event in core.bank.journal.events()
                  if event["data"].get("experiment") == "bean_sketch_v1"]
        assert trials[0]["error"] == failed["error"]
        assert trials[0]["raw_sha256"] == failed["raw_sha256"]
        assert trials[1]["svg_file"] == "attempt_02.svg"
    finally:
        core.close()


def test_real_image_feedback_and_coordinate_convention_reach_revision_prompt(tmp_path):
    pytest.importorskip("cairosvg")
    model = FakeModel([drawing(), review(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.sqlite3", model=model)
    feedback = "Synthetic evaluator sees a different subject; intended subject is absent."

    def judge(png, subject):
        assert Path(png).is_file()
        return {"image_sha256": file_hash(png), "kind": "vision_model",
                "evaluator": "synthetic evaluator callback", "satisfactory": False,
                "feedback": feedback, "scores": {"subject_recognition": 4}}

    try:
        SketchLab(core, visual_judge=judge).run(
            task_ref="synthetic-priority", output_dir=tmp_path / "out",
            subject="synthetic subject", max_attempts=2, backend="stdlib")
        draw_calls = [query for query in model.requests
                      if query.startswith("Draw your chosen subject, ")]
        assert len(draw_calls) == 2
        assert "x increases to the right; y increases downward" in draw_calls[0]
        assert feedback in draw_calls[1]
        assert "recognizing a different subject means the intended subject failed" in draw_calls[1]
        assert "Revise the failed relationships" in draw_calls[1]
        retained = json.loads((tmp_path / "out" / "attempt_01.json").read_text())
        assert retained["external_feedback"]["scores"]["subject_recognition"] == 4
        assert retained["external_feedback"]["satisfactory"] is False
        assert retained["independent_visual_verification"] is False
    finally:
        core.close()

"""Synthetic mechanism regressions, never evidence of live creative output."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest

from bean.creativity.artifacts import FileVisionReviewer, file_hash, validate_feedback
from bean.creativity.sketch_lab import SketchLab, execution_mode, OllamaSketchProvider
from bean.learning import NativeReasoningService
from bean.tests.test_sketch_lab import FakeModel, plan, drawing, review


def read_json(path):
    return json.loads(Path(path).read_text())


@pytest.mark.parametrize("model", [
    FakeModel([]),
    type("SpoofedLiveModel", (), {
        "provider_kind": "ollama", "model_id": "claimed-real-provider",
        "complete": lambda *args: drawing(),
    })(),
])
def test_require_live_rejects_scripted_and_spoofed_provider_with_receipt(tmp_path, model):
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    try:
        with pytest.raises(ValueError, match="Live run requires"):
            SketchLab(core).run(task_ref="synthetic-rejected", output_dir=tmp_path / "out",
                                require_live=True)
        manifest = read_json(tmp_path / "out" / "run.json")
        assert manifest["state"] == "run_failed"
        assert manifest["attempts"] == 0
        assert manifest["execution_mode"] != "live_model"
        assert manifest["journal_tip"]
        assert read_json(tmp_path / "out" / "model_calls.json") == []
        assert not list((tmp_path / "out").glob("*.svg"))
    finally:
        core.close()


def test_subclass_cannot_inherit_live_attestation():
    class SyntheticSubclass(OllamaSketchProvider):
        def complete(self, *args, **kwargs):
            return drawing()
    assert execution_mode(SyntheticSubclass()) == "unverified"


def test_live_requirement_rejects_injected_scripted_ollama_transport(tmp_path):
    class ScriptedTransport:
        def __init__(self):
            self.answers = iter([plan(), drawing(), review()])
        def _json(self, *args, **kwargs):
            return {"models": [{"name": "synthetic-pretend-model", "digest": "a" * 64}]}
        def chat_json(self, *args, **kwargs):
            return next(self.answers)
    model = OllamaSketchProvider(model_name="synthetic-pretend-model", client=ScriptedTransport())
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    try:
        with pytest.raises(ValueError, match="transport|client|Live"):
            SketchLab(core).run(task_ref="synthetic-injected-transport",
                                output_dir=tmp_path / "out", require_live=True,
                                max_attempts=1, backend="stdlib")
    finally:
        core.close()


def test_missing_model_preserves_failure_and_does_not_make_art(tmp_path):
    core = NativeReasoningService(tmp_path / "core.db", model=None)
    try:
        with pytest.raises(ValueError):
            SketchLab(core).run(task_ref="missing-provider", output_dir=tmp_path / "out",
                                require_live=True)
        manifest = read_json(tmp_path / "out" / "run.json")
        assert manifest["state"] == "run_failed"
        assert manifest["error"]
        assert manifest["attempts"] == 0
        assert manifest["independent_visual_verification"] is False
        events = [e["data"] for e in core.bank.journal.events()
                  if e["data"].get("experiment") == "bean_sketch_run_v1"]
        assert len(events) == 1 and events[0]["state"] == "run_failed"
        assert not list((tmp_path / "out").glob("*.png"))
    finally:
        core.close()


def test_invalid_output_retained_and_next_attempt_gets_error(tmp_path):
    invalid = '{"description":"bad primitive","shapes":[{"type":"script"}]}'
    model = FakeModel([invalid, drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    try:
        outcome = SketchLab(core).run(task_ref="synthetic-invalid", output_dir=tmp_path / "out",
                                     subject="a bicycle", max_attempts=2, backend="stdlib")
        assert outcome["attempts"] == 2
        failed = read_json(tmp_path / "out" / "attempt_01.json")
        assert failed["status"] == "attempt_failed_ValueError"
        assert "Unsupported primitive" in failed["error"]
        assert failed["svg_file"] is None and failed["png_file"] is None
        raw = tmp_path / "out" / failed["raw_file"]
        assert file_hash(raw) == failed["raw_sha256"]
        assert read_json(raw)[0]["response"] == invalid
        assert "Unsupported primitive" in model.requests[1]
        assert "bad primitive" in model.requests[1]
        assert read_json(tmp_path / "out" / "attempt_02.json")["verification_state"] == "artifacts_verified"
    finally:
        core.close()


def test_real_png_bytes_and_all_recorded_artifact_hashes(tmp_path):
    model = FakeModel([plan(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    try:
        result = SketchLab(core).run(task_ref="synthetic-preview", output_dir=tmp_path / "out",
                                     max_attempts=1, backend="stdlib")
        history = result["history"][0]
        row = read_json(history["metadata"])
        assert row["execution_mode"] == "synthetic_fixture"
        assert row["subject_source"] == "autonomous"
        assert row["created_at_utc"] and row["source_git_sha"]
        assert row["verification_state"] == "artifacts_verified"
        assert row["external_feedback"]["state"] == "unavailable"
        for path, expected in ((history["svg"], row["svg_sha256"]),
                               (history["png"], row["png_sha256"]),
                               (history["metadata"], history["metadata_sha256"]),
                               (tmp_path / "out" / row["raw_file"], row["raw_sha256"])):
            assert sha256(Path(path).read_bytes()).hexdigest() == expected
        with Image.open(history["png"]) as image:
            image.load()
            assert image.format == "PNG" and image.size == (512, 512)
            # Pixels must contain actual rendered lines and white background.
            assert image.convert("L").getextrema() == (0, 255)
        assert row["independent_visual_verification"] is False
        assert row["weights_updated"] is False
    finally:
        core.close()


def test_preview_failure_retains_svg_without_inventing_preview(tmp_path, monkeypatch):
    def unavailable(*args):
        raise RuntimeError("synthetic rasterizer failure")
    monkeypatch.setattr("bean.creativity.sketch_lab.rasterize", unavailable)
    core = NativeReasoningService(tmp_path / "core.db", model=FakeModel([plan(), drawing(), review()]))
    try:
        result = SketchLab(core).run(task_ref="synthetic-no-preview", output_dir=tmp_path / "out",
                                     max_attempts=1, backend="stdlib")
        row = read_json(result["history"][0]["metadata"])
        assert row["svg_sha256"]
        assert row["png_file"] is None
        assert "synthetic rasterizer failure" in row["preview_error"]
        assert row["verification_state"] == "incomplete"
        assert not list((tmp_path / "out").glob("*.png"))
    finally:
        core.close()


def test_output_reuse_cannot_overwrite_retained_attempts(tmp_path):
    core = NativeReasoningService(tmp_path / "core.db", model=FakeModel([plan(), drawing(), review()]))
    try:
        lab = SketchLab(core)
        lab.run(task_ref="synthetic-original", output_dir=tmp_path / "out",
                max_attempts=1, backend="stdlib")
        hashes = {p.name: file_hash(p) for p in (tmp_path / "out").iterdir()}
        with pytest.raises(ValueError, match="already contains a run"):
            lab.run(task_ref="must-not-overwrite", output_dir=tmp_path / "out")
        assert {p.name: file_hash(p) for p in (tmp_path / "out").iterdir()} == hashes
    finally:
        core.close()


def test_hash_bound_pixel_feedback_reaches_revision_prompt(tmp_path):
    model = FakeModel([plan(), drawing(), review(), drawing(), review()])
    core = NativeReasoningService(tmp_path / "core.db", model=model)
    inspected = []
    def synthetic_judge(png, subject):
        with Image.open(png) as image:
            image.load()
            inspected.append((image.size, subject, file_hash(png)))
        return {"image_sha256": file_hash(png), "kind": "vision_model",
                "evaluator": "synthetic-test-evaluator", "satisfactory": False,
                "feedback": "synthetic pixel-review observation: separate wheel overlap",
                "scores": {"composition": 1}}
    try:
        result = SketchLab(core, visual_judge=synthetic_judge).run(
            task_ref="synthetic-pixel-feedback", output_dir=tmp_path / "out",
            max_attempts=2, backend="stdlib")
        assert len(inspected) == 2
        assert all(size == (512, 512) for size, _, _ in inspected)
        assert "separate wheel overlap" in model.requests[3]
        row = read_json(result["history"][0]["metadata"])
        assert row["external_feedback"]["image_sha256"] == row["png_sha256"]
        assert row["external_feedback"]["state"] == "host_reported_pixel_review"
        assert row["external_feedback"]["independently_authenticated"] is False
        assert row["independent_visual_verification"] is False
    finally:
        core.close()


def test_wrong_image_feedback_fails_and_legacy_report_stays_unverified(tmp_path):
    for name, report in (("wrong-hash", {"image_sha256": "0" * 64, "kind": "human",
                                        "evaluator": "synthetic-test", "satisfactory": True,
                                        "feedback": "synthetic claim"}),
                         ("legacy", {"satisfactory": True, "feedback": "synthetic legacy claim"})):
        core = NativeReasoningService(tmp_path / (name + ".db"),
                                      model=FakeModel([plan(), drawing(), review()]))
        try:
            result = SketchLab(core, visual_judge=lambda *args: report).run(
                task_ref="synthetic-" + name, output_dir=tmp_path / name,
                max_attempts=1, backend="stdlib")
            row = read_json(result["history"][0]["metadata"])
            if name == "wrong-hash":
                assert row["status"] == "attempt_failed_ValueError"
                assert "actual PNG hash" in row["error"]
            else:
                assert row["external_feedback"]["state"] == "legacy_host_report_unverified"
            assert row["independent_visual_verification"] is False
        finally:
            core.close()


def test_file_reviewer_records_unavailable_and_requires_matching_hash(tmp_path):
    png = tmp_path / "image.png"
    Image.new("RGB", (512, 512), "white").save(png)
    reviewer = FileVisionReviewer(tmp_path / "feedback")
    assert reviewer(png, "synthetic subject")["state"] == "unavailable"
    digest = file_hash(png)
    request = read_json(tmp_path / "feedback" / (digest + ".request.json"))
    assert request["image_sha256"] == digest
    assert Path(request["image"]) == png.resolve()
    report = {"image_sha256": "0" * 64, "kind": "vision_model",
              "evaluator": "synthetic-test", "satisfactory": False, "feedback": "fixture"}
    with pytest.raises(ValueError, match="actual PNG hash"):
        validate_feedback(report, png)


def test_core_feedback_and_failed_drafts_survive_separate_processes(tmp_path):
    root = Path(__file__).resolve().parents[2]
    first = r'''
import json, sys
from pathlib import Path
from bean.learning import NativeReasoningService
from bean.creativity.sketch_lab import SketchLab
from bean.creativity.artifacts import file_hash
from bean.tests.test_sketch_lab import FakeModel, drawing, review
folder = Path(sys.argv[1])
model = FakeModel(['{"description":"invalid","shapes":[{"type":"script"}]}', drawing(), review()])
core = NativeReasoningService(folder / 'restart.db', model=model)
def judge(png, subject):
 return {'image_sha256':file_hash(png), 'kind':'vision_model', 'evaluator':'synthetic-test-only',
         'satisfactory':False, 'feedback':'retained synthetic external observation'}
try:
 SketchLab(core, visual_judge=judge).run(task_ref='synthetic-before-restart',
   output_dir=folder/'first', subject='synthetic persistent subject', max_attempts=2, backend='stdlib')
finally:
 core.close()
'''
    second = r'''
import json, sys
from pathlib import Path
from bean.learning import NativeReasoningService
from bean.creativity.sketch_lab import SketchLab
from bean.tests.test_sketch_lab import FakeModel, plan, drawing, review
folder = Path(sys.argv[1])
model = FakeModel([plan('synthetic new subject'), drawing(), review()])
core = NativeReasoningService(folder / 'restart.db', model=model)
try:
 events=[e['data'] for e in core.bank.journal.events() if e['data'].get('experiment')=='bean_sketch_v1']
 assert len(events)==2
 assert events[0]['status']=='attempt_failed_ValueError'
 assert events[1]['external_feedback']['feedback']=='retained synthetic external observation'
 SketchLab(core).run(task_ref='synthetic-after-restart', output_dir=folder/'second',
   max_attempts=1, backend='stdlib')
 assert 'synthetic persistent subject' in model.requests[0]
 assert 'retained synthetic external observation' in model.requests[0]
 assert 'retained synthetic external observation' in model.requests[1]
 print(json.dumps({'prior_trials':len(events), 'feedback_recalled':True}))
finally:
 core.close()
'''
    subprocess.run([sys.executable, "-c", first, str(tmp_path)], cwd=root, check=True,
                   capture_output=True, text=True, timeout=30)
    completed = subprocess.run([sys.executable, "-c", second, str(tmp_path)], cwd=root,
                               check=True, capture_output=True, text=True, timeout=30)
    assert json.loads(completed.stdout) == {"prior_trials": 2, "feedback_recalled": True}
    assert (tmp_path / "first" / "attempt_01.raw.json").is_file()
    assert (tmp_path / "first" / "attempt_02.svg").is_file()
    assert (tmp_path / "second" / "attempt_01.png").is_file()

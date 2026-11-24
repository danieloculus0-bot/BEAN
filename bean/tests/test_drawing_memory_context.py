"""Synthetic memory-delivery contracts, not evidence of artistic learning.

The model replies below are labeled fixtures. The tests inspect actual Core
SQLite persistence and the prompts delivered after reopening separate Python
processes; generated test SVGs are never published as genuine artwork.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from bean.creativity import sketch_lab
from bean.learning import NativeReasoningService
from bean.tests.test_sketch_lab import FakeModel, drawing, review


ROOT = Path(__file__).resolve().parents[2]


def large_trial(subject, task_ref, attempt, marker):
    """Realistic verbose vision provenance that previously filled the prefix."""
    return {
        "schema": "bean.adaptive_lab026.v1",
        "experiment": "bean_sketch_v1", "domain": "sketch",
        "task_ref": task_ref, "attempt": attempt, "subject": subject,
        "status": "host_reported_not_satisfactory",
        "error": "Synthetic retained validation observation " + "detail " * 80,
        "self_review": {"changes": marker + " self-critique " * 180},
        "external_feedback": {
            "state": "host_reported_pixel_review", "kind": "vision_model",
            "evaluator": "synthetic-memory-context-fixture",
            "provider_kind": "ollama", "model_id": "synthetic-vision-fixture",
            "model_digest": "b" * 64, "image_sha256": "c" * 64,
            "evaluation_protocol": "blind_then_targeted_min_v1",
            "recognized_subject": "unclear " + marker,
            "observations": marker + " disconnected visible marks " * 140,
            "feedback": marker + " needs recognizable relationships " * 160,
            "scores": {"spatial_coherence": 1, "subject_recognition": 0,
                       "composition": 1},
            "satisfactory": False,
        },
    }


def test_context_retains_newest_feedback_as_complete_bounded_json():
    prior = [large_trial("a teapot", "old-training", i, "OLD_TEAPOT")
             for i in range(1, 6)]
    prior.append(large_trial("a cat", "heldout-cat", 2, "NEW_CAT_EVIDENCE_猫"))
    original = deepcopy(prior)
    context = sketch_lab.drawing_memory_context(prior, budget=2400)
    records = json.loads(context)
    assert len(context) <= 2400
    assert isinstance(records, list) and records
    assert records[0]["subject"] == "a cat"
    assert records[0]["task_ref"] == "heldout-cat"
    assert records[0]["attempt"] == 2
    assert "NEW_CAT_EVIDENCE_猫" in context
    assert records[0]["external_feedback"]["scores"]["subject_recognition"] == 0
    assert prior == original, "Retrieval must not rewrite the evidence journal data"


def test_frozen_snapshot_and_empty_memory_do_not_acquire_later_feedback():
    frozen = [large_trial("a teapot", "training", i, "TRAINING_FEEDBACK")
              for i in (1, 2)]
    frozen_before = deepcopy(frozen)
    adaptive = frozen + [large_trial("a cat", "heldout-cat", 1, "NEW_CAT_FEEDBACK")]
    frozen_context = sketch_lab.drawing_memory_context(frozen)
    adaptive_context = sketch_lab.drawing_memory_context(adaptive)
    assert "NEW_CAT_FEEDBACK" in adaptive_context
    assert "NEW_CAT_FEEDBACK" not in frozen_context
    assert adaptive_context != frozen_context
    assert frozen == frozen_before
    assert json.loads(sketch_lab.drawing_memory_context([])) == []


def _child(code, *args):
    completed = subprocess.run([sys.executable, "-c", code, *map(str, args)],
                               cwd=ROOT, text=True, capture_output=True,
                               check=True, timeout=60)
    return json.loads(completed.stdout)


def _append_in_new_process(db, fixture_path):
    return _child("""
import json, sys
from bean.learning import NativeReasoningService
core = NativeReasoningService(sys.argv[1])
try:
    for data in json.load(open(sys.argv[2], encoding='utf-8')):
        core.bank.record_trial(data)
    core.bank.journal.verify()
    print(json.dumps({'events': len(core.bank.journal.events())}))
finally:
    core.close()
""", db, fixture_path)


def test_separate_processes_deliver_recent_feedback_to_second_heldout_prompt(tmp_path):
    """Actual persisted retrieval differs; no score/learning claim is inferred."""
    training = [large_trial("a teapot", "training", i, "TEAPOT_TRAINING_ONLY")
                for i in (1, 2)]
    earlier_heldout = [large_trial("a cat", "heldout-cat", i, "CAT_AFTER_RESTART")
                       for i in (1, 2)]
    training_path, cat_path = tmp_path / "training.json", tmp_path / "cat.json"
    training_path.write_text(json.dumps(training), encoding="utf-8")
    cat_path.write_text(json.dumps(earlier_heldout), encoding="utf-8")
    frozen_path = tmp_path / "frozen-memory.json"
    frozen_path.write_text(json.dumps(training), encoding="utf-8")
    source = tmp_path / "source.sqlite3"
    assert _append_in_new_process(source, training_path)["events"] == 2
    assert _append_in_new_process(source, cat_path)["events"] == 4

    reader = """
import json, sys
from pathlib import Path
from bean.learning import NativeReasoningService
from bean.creativity.sketch_lab import SketchLab
from bean.tests.test_sketch_lab import FakeModel, drawing, review
db, out, mode, frozen_file = sys.argv[1:]
model = FakeModel([drawing(), review()])
core = NativeReasoningService(db, model=model)
try:
    SketchLab(core).run(task_ref='benchmark-heldout-' + mode + '-02',
                        output_dir=out, subject='a sailboat', max_attempts=1,
                        backend='stdlib', memory_mode=mode,
                        frozen_memory=json.load(open(frozen_file, encoding='utf-8'))
                        if mode == 'frozen' else None)
    run = json.loads((Path(out) / 'run.json').read_text())
    print(json.dumps({'requests': model.requests,
                      'context': run.get('memory_context_records'),
                      'context_sha256': run['memory_context_sha256']}))
finally:
    core.close()
"""
    results = {}
    for mode in ("adaptive", "frozen", "none"):
        db = tmp_path / (mode + ".sqlite3")
        with sqlite3.connect(source) as original, sqlite3.connect(db) as copy:
            original.backup(copy)
        results[mode] = _child(reader, db, tmp_path / mode, mode, frozen_path)

    adaptive, frozen, none = (results[x] for x in ("adaptive", "frozen", "none"))
    # These are the actual drawing prompts received by separate fixture model
    # instances after Core reopening, rather than inferred retrieval counters.
    assert "CAT_AFTER_RESTART" in adaptive["requests"][0]
    assert "CAT_AFTER_RESTART" not in frozen["requests"][0]
    assert "TEAPOT_TRAINING_ONLY" in frozen["requests"][0]
    assert "CAT_AFTER_RESTART" not in none["requests"][0]
    assert "TEAPOT_TRAINING_ONLY" not in none["requests"][0]
    assert adaptive["requests"][0] != frozen["requests"][0]
    assert adaptive["context_sha256"] != frozen["context_sha256"]
    assert none["context_sha256"] == sha256(b"[]").hexdigest()
    assert isinstance(adaptive["context"], list)
    assert adaptive["context"][0]["subject"] == "a cat"
    assert all(row["subject"] == "a teapot" for row in frozen["context"])
    assert none["context"] == []
    # Reading an adaptive journal must not contaminate the frozen snapshot.
    assert json.loads(frozen_path.read_text()) == training


def _description_drawing(description):
    reply = json.loads(drawing())
    reply["description"] = description
    return json.dumps(reply)


def test_337_character_model_description_keeps_original_text_and_renders(tmp_path):
    try:
        import cairosvg  # noqa: F401 - positive preview test needs actual pixels
        from PIL import Image  # noqa: F401
    except (ImportError, OSError) as exc:
        pytest.skip("Optional local PNG renderer unavailable: " + str(exc))
    description = ("Synthetic extended model description. " * 12)[:337]
    assert len(description) == 337
    model = FakeModel([_description_drawing(description), review()])
    core = NativeReasoningService(tmp_path / "core.sqlite3", model=model)
    try:
        result = sketch_lab.SketchLab(core).run(
            task_ref="synthetic-long-description", output_dir=tmp_path / "out",
            subject="a bicycle", max_attempts=1, backend="stdlib")
        row = json.loads(Path(result["history"][0]["metadata"]).read_text())
        assert row["description"] == description
        assert row["verification_state"] == "artifacts_verified"
        assert row["svg_file"] and row["png_file"]
        assert row["execution_mode"] == "synthetic_fixture"
        png = tmp_path / "out" / row["png_file"]
        assert sha256(png.read_bytes()).hexdigest() == row["png_sha256"]
        with Image.open(png) as image:
            image.load()
            assert image.format == "PNG" and image.size == (512, 512)
        calls = json.loads((tmp_path / "out" / row["raw_file"]).read_text())
        assert json.loads(calls[0]["response"])["description"] == description
    finally:
        core.close()


def test_description_above_1000_characters_retains_failed_response(tmp_path):
    description = "Synthetic description " + "x" * 1001
    model = FakeModel([_description_drawing(description)])
    core = NativeReasoningService(tmp_path / "core.sqlite3", model=model)
    try:
        result = sketch_lab.SketchLab(core).run(
            task_ref="synthetic-description-over-budget", output_dir=tmp_path / "out",
            subject="a bicycle", max_attempts=1, backend="stdlib")
        row = json.loads(Path(result["history"][0]["metadata"]).read_text())
        assert row["status"] == "attempt_failed_ValueError"
        assert row["error"]
        assert row["svg_file"] is None and row["png_file"] is None
        calls = json.loads((tmp_path / "out" / row["raw_file"]).read_text())
        assert json.loads(calls[0]["response"])["description"] == description
        trials = [event["data"] for event in core.bank.journal.events()
                  if event["data"].get("experiment") == "bean_sketch_v1"]
        assert len(trials) == 1 and trials[0]["status"] == row["status"]
    finally:
        core.close()

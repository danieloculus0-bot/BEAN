"""Synthetic protocol tests; these do not certify BEAN's artistic skill."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from bean.creativity.drawing_benchmark import (
    ARMS, execute, protocol, summarize, validate_protocol, write_json,
)


def test_protocol_is_frozen_and_holdout_disjoint():
    spec = protocol(["a lighthouse"], ["a telescope", "a teapot"], seed=4)
    assert validate_protocol(spec) == spec
    with pytest.raises(ValueError, match="disjoint"):
        protocol(["A Lighthouse"], ["a lighthouse"])
    changed = {**spec, "attempts": 3}
    with pytest.raises(ValueError, match="digest"):
        validate_protocol(changed)
    with pytest.raises(ValueError):
        protocol(["a lighthouse"], ["a teapot"], attempts=1)


def test_matched_cells_reopen_real_core_and_freeze_before_holdout(tmp_path):
    """Fresh subprocesses write real SHA trials, without generating fake art."""
    commands = []
    def runner(command, **kwargs):
        commands.append(command)
        db = command[command.index("--db") + 1]
        subject = command[command.index("--subject") + 1]
        child = (
            "import json,sys; from bean.learning import NativeReasoningService; "
            "c=NativeReasoningService(sys.argv[1]); "
            "before=len(c.bank.journal.events()); "
            "c.bank.record_trial({'schema':'bean.adaptive_lab026.v1','experiment':'bean_sketch_v1',"
            "'subject':sys.argv[2],'status':'synthetic_protocol_test'}); "
            "print(json.dumps({'before':before})); c.close()"
        )
        return subprocess.run([sys.executable, "-c", child, db, subject], **kwargs)
    spec = protocol(["a lighthouse"], ["a telescope", "a teapot"], seed=17)
    out = tmp_path / "benchmark"
    result = execute(spec, out, runner=runner, review_dir=tmp_path / "reviews", review_wait=3)
    assert len(commands) == 1 + 3 * 2
    frozen = json.loads((out / "frozen-memory.json").read_text())
    assert [x["subject"] for x in frozen] == ["a lighthouse"]
    for subject in spec["heldout_subjects"]:
        matched = [cmd for cmd in commands if cmd[cmd.index("--subject") + 1] == subject]
        assert len(matched) == 3
        assert {cmd[cmd.index("--memory-mode") + 1] for cmd in matched} == set(ARMS)
        assert len({cmd[cmd.index("--seed") + 1] for cmd in matched}) == 1
        assert all(cmd[cmd.index("--attempts") + 1] == "2" for cmd in matched)
        assert all("--require-live" in cmd and "--all-attempts" in cmd for cmd in matched)
        assert all(cmd[cmd.index("--review-wait") + 1] == "3" for cmd in matched)
    adaptive_second = next(x for x in result["outcomes"]
                           if x["phase"] == "heldout" and x["arm"] == "adaptive"
                           and x["challenge"] == 2)
    assert adaptive_second["process_returncode"] == 0
    stdout = out / "heldout/adaptive/challenge_02/stdout.txt"
    assert json.loads(stdout.read_text())["before"] == 2
    assert all(value is None for value in result["heldout_last_attempt_means"]["adaptive"].values())
    assert result["learning_improvement_verified"] is False
    with pytest.raises(ValueError, match="empty"):
        execute(spec, out, runner=runner)


def _summary_fixture(tmp_path):
    # Construct a wholly synthetic receipt contract, with valid rendered PNGs.
    # This mocks the provider provenance for verifier tests only; no output is
    # published or represented as a genuine provider run.
    try:
        import cairosvg  # noqa: F401 - tests below require a real rasterizer
    except (ImportError, OSError) as exc:
        pytest.skip("Optional PNG renderer unavailable: " + str(exc))
    from bean.creativity.sketch_lab import draw_svg
    from bean.creativity.artifacts import rasterize
    spec = protocol(["a lighthouse"], ["a teapot"], seed=1)
    write_json(tmp_path / "protocol.json", spec)
    cells = []
    for arm in ARMS:
        folder = tmp_path / "heldout" / arm / "challenge_01" / "attempts"
        folder.mkdir(parents=True)
        history = []
        calls = [{"response": "Synthetic scoring contract input, never live art"}]
        write_json(folder / "model_calls.json", calls)
        common = {"model_id": "synthetic-scoring-contract", "provider_kind": "ollama",
                  "model_digest": "fixture-digest", "source_git_sha": "a" * 40,
                  "run_id": "synthetic-scoring-contract-" + arm,
                  "execution_mode": "live_model", "subject": "a teapot",
                  "subject_source": "human", "memory_mode": arm, "seed": 2}
        for attempt, score in ((1, 1), (2, 3 if arm == "adaptive" else 2)):
            name = "attempt_%02d" % attempt
            svg_digest = draw_svg([{"type": "circle", "cx": 128, "cy": 128, "r": 60}],
                                  folder / (name + ".svg"), "stdlib")
            preview = rasterize(folder / (name + ".svg"), folder / (name + ".png"))
            digest = preview["png_sha256"]
            write_json(folder / (name + ".raw.json"), calls)
            write_json(folder / (name + ".json"), {
                **common, "schema": "bean.draw.attempt.v1", "attempt": attempt,
                "status": "synthetic_scoring_contract",
                "verification_state": "artifacts_verified",
                "svg_file": name + ".svg", "svg_sha256": svg_digest,
                "png_file": name + ".png", "png_sha256": digest,
                "raw_file": name + ".raw.json",
                "raw_sha256": sha256((folder / (name + ".raw.json")).read_bytes()).hexdigest(),
                "external_feedback": {
                    "kind": "vision_model", "image_sha256": digest,
                    "evaluator": "synthetic-scoring-contract",
                    "satisfactory": False, "feedback": "Scoring-contract test only",
                    "scores": {"spatial_coherence": score,
                               "subject_recognition": score, "composition": score},
                },
            })
            history.append({"attempt": attempt, "metadata": name + ".json",
                            "metadata_sha256": sha256((folder / (name + ".json")).read_bytes()).hexdigest(),
                            "sha256": svg_digest, "png_sha256": digest})
        write_json(folder / "run.json", {
            **common, "schema": "bean.draw.run.v1", "attempts": 2, "history": history,
            "model_calls_sha256": sha256((folder / "model_calls.json").read_bytes()).hexdigest(),
            "completed_at_utc": "2026-11-19T00:00:00+00:00", "state": "host_reported_not_satisfactory",
        })
        cells.append({"phase": "heldout", "arm": arm, "challenge": 1,
                      "subject": "a teapot", "returncode": 0, "seed": 2,
                      "folder": str(folder.parent.relative_to(tmp_path))})
    write_json(tmp_path / "execution.json", {
        "protocol_sha256": spec["protocol_sha256"], "cells": cells,
    })
    return tmp_path / "heldout/adaptive/challenge_01/attempts/attempt_02.json"


def test_reviews_need_actual_matching_image_hash_and_live_execution(tmp_path):
    sidecar = _summary_fixture(tmp_path)
    scores = summarize(tmp_path)
    assert scores["iteration_quality_last_minus_first"]["adaptive"]["composition"] == 2
    assert scores["generalization_adaptive_minus_control"]["frozen"]["composition"] == 1
    assert scores["heldout_last_attempt_means"]["adaptive"]["diversity"] is None
    assert scores["learning_improvement_verified"] is False
    row = json.loads(sidecar.read_text())
    row["external_feedback"]["image_sha256"] = "0" * 64
    write_json(sidecar, row)
    assert summarize(tmp_path)["heldout_last_attempt_means"]["adaptive"]["composition"] is None
    row["external_feedback"]["image_sha256"] = row["png_sha256"]
    row["execution_mode"] = "synthetic_fixture"
    write_json(sidecar, row)
    assert summarize(tmp_path)["heldout_last_attempt_means"]["adaptive"]["composition"] is None


def test_missing_and_invalid_scores_stay_unknown(tmp_path):
    sidecar = _summary_fixture(tmp_path)
    row = json.loads(sidecar.read_text())
    row["external_feedback"]["scores"] = {
        "spatial_coherence": True, "subject_recognition": float("nan"),
        "composition": 5,
    }
    write_json(sidecar, row)
    report = summarize(tmp_path)
    assert all(value is None for value in report["heldout_last_attempt_means"]["adaptive"].values())
    assert all(value is None for value in report["generalization_adaptive_minus_control"]["none"].values())


def test_provider_failure_preserves_every_cell(tmp_path):
    def offline(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, "", "provider unavailable")
    output = tmp_path / "offline"
    result = execute(protocol(["a lighthouse"], ["a telescope"]), output,
                     runner=offline)
    assert len(result["outcomes"]) == 4
    assert all(row["process_returncode"] == 2 for row in result["outcomes"])
    assert (output / "heldout/frozen/challenge_01/stderr.txt").read_text() == "provider unavailable"
    assert result["learning_improvement_verified"] is False


def test_unmatched_model_and_partial_budget_cannot_earn_control_delta(tmp_path):
    sidecar = _summary_fixture(tmp_path)
    row = json.loads(sidecar.read_text())
    row["model_digest"] = "a-different-model"
    write_json(sidecar, row)
    result = summarize(tmp_path)
    assert result["matched_heldout_comparison_counts"]["frozen"]["composition"] == 0
    assert result["generalization_adaptive_minus_control"]["frozen"]["composition"] is None
    row["model_digest"] = "fixture-digest"
    write_json(sidecar, row)
    sidecar.with_name("attempt_01.json").unlink()
    assert summarize(tmp_path)["generalization_adaptive_minus_control"]["none"]["composition"] is None


def test_portfolio_diversity_requires_joint_hash_bound_review(tmp_path):
    sidecar = _summary_fixture(tmp_path)
    digest = json.loads(sidecar.read_text())["png_sha256"]
    assert summarize(tmp_path)["portfolio_diversity"]["adaptive"] is None
    report = {"schema": "bean.draw.portfolio_review.v1", "kind": "vision_model",
              "evaluator": "synthetic-scoring-contract", "feedback": "Test only",
              "image_sha256s": [digest], "diversity": 2}
    path = tmp_path / "portfolio-review.adaptive.json"
    write_json(path, report)
    assert summarize(tmp_path)["portfolio_diversity"]["adaptive"]["score"] == 2
    report["image_sha256s"] = ["0" * 64]
    write_json(path, report)
    assert summarize(tmp_path)["portfolio_diversity"]["adaptive"] is None


@pytest.mark.parametrize("broken", ["png", "svg", "raw", "calls", "failed_process", "fixture_identity"])
def test_broken_run_chain_cannot_earn_scores(tmp_path, broken):
    sidecar = _summary_fixture(tmp_path)
    folder = sidecar.parent
    if broken == "failed_process":
        path = tmp_path / "execution.json"
        record = json.loads(path.read_text())
        record["cells"][0]["returncode"] = 2
        write_json(path, record)
    elif broken == "fixture_identity":
        path = folder / "run.json"
        record = json.loads(path.read_text())
        record["provider_kind"] = "synthetic_fixture"
        write_json(path, record)
    else:
        filename = {"png": "attempt_02.png", "svg": "attempt_02.svg",
                    "raw": "attempt_02.raw.json", "calls": "model_calls.json"}[broken]
        (folder / filename).write_bytes(b"tampered")
    result = summarize(tmp_path)
    adaptive = next(x for x in result["outcomes"] if x["arm"] == "adaptive")
    assert adaptive["artifact_verification_error"]
    assert result["heldout_last_attempt_means"]["adaptive"]["composition"] is None
    assert result["generalization_adaptive_minus_control"]["frozen"]["composition"] is None


def test_hash_bound_non_png_is_rejected_even_with_rebound_receipts(tmp_path):
    sidecar = _summary_fixture(tmp_path)
    folder = sidecar.parent
    (folder / "attempt_02.png").write_bytes(b"not an image")
    digest = sha256(b"not an image").hexdigest()
    row = json.loads(sidecar.read_text())
    row["png_sha256"] = row["external_feedback"]["image_sha256"] = digest
    write_json(sidecar, row)
    run = json.loads((folder / "run.json").read_text())
    run["history"][1]["png_sha256"] = digest
    run["history"][1]["metadata_sha256"] = sha256(sidecar.read_bytes()).hexdigest()
    write_json(folder / "run.json", run)
    assert summarize(tmp_path)["heldout_last_attempt_means"]["adaptive"]["composition"] is None

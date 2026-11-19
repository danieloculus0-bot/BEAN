"""Matched drawing challenges over SketchLab, not a second drawing engine.

Protocol subjects are human-assisted challenges, never autonomous subject
choices. Every task runs in a new Python process against the existing Core
SQLite/SHA journal. Scores require image-hash-bound external pixel reviews;
neither textual self-critique nor different SVG bytes establish improvement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

SCHEMA = "bean.draw.benchmark.v1"
ARMS = ("adaptive", "frozen", "none")
METRICS = ("spatial_coherence", "subject_recognition", "composition")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True,
                                    ensure_ascii=False) + "\n", encoding="utf-8")


def _subjects(values):
    if (not isinstance(values, list) or not 1 <= len(values) <= 30
            or any(not isinstance(x, str) or not x.strip() or len(x) > 120
                   for x in values)):
        raise ValueError("Need 1..30 bounded, nonempty subjects")
    result = [x.strip() for x in values]
    if len({x.casefold() for x in result}) != len(result):
        raise ValueError("Challenge subjects must be distinct")
    return result


def protocol(training_subjects, heldout_subjects, *, seed=20261119, attempts=2):
    """Freeze a challenge specification before generation or evaluation."""
    training, heldout = _subjects(training_subjects), _subjects(heldout_subjects)
    if {x.casefold() for x in training} & {x.casefold() for x in heldout}:
        raise ValueError("Training and held-out subjects must be disjoint")
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError("Seed must be a nonnegative 31-bit integer")
    if type(attempts) is not int or not 2 <= attempts <= 5:
        raise ValueError("Need 2..5 retained attempts per challenge")
    specification = {
        "schema": SCHEMA, "training_subjects": training,
        "heldout_subjects": heldout, "subject_source": "human_protocol",
        "seed": seed, "attempts": attempts, "arms": list(ARMS),
        "score_scale": {"minimum": 0, "maximum": 4},
        "metrics": list(METRICS),
        "design": "shared_training_then_matched_heldout_separate_processes",
        "weights_updated": False,
    }
    return {**specification, "protocol_sha256": sha256(canonical(specification)).hexdigest()}


def validate_protocol(specification):
    expected = protocol(specification["training_subjects"],
                        specification["heldout_subjects"],
                        seed=specification["seed"], attempts=specification["attempts"])
    if specification != expected:
        raise ValueError("Protocol changed or contains an invalid digest")
    return expected


def _backup(source, target):
    with sqlite3.connect("file:" + str(Path(source).resolve()) + "?mode=ro",
                         uri=True) as original, sqlite3.connect(target) as copy:
        original.backup(copy)


def _trials(db):
    # Existing Core verifies its journal chain while reading. No private
    # checkpoint is loaded unless the caller explicitly supplied that DB.
    from bean.learning import NativeReasoningService
    core = NativeReasoningService(db)
    try:
        return [event["data"] for event in core.bank.journal.events()
                if event.get("kind") == "trial"
                and event["data"].get("experiment") == "bean_sketch_v1"]
    finally:
        core.close()


def execute(specification, output, *, baseline_db=None, python=sys.executable,
            review_dir=None, review_wait=0, runner=subprocess.run):
    """Run a precommitted protocol; preserve stdout, errors, failed cells.

    The configured BEAN provider is inherited by all child processes. No
    provider fallback, subject geometry, or canned model response is supplied.
    """
    spec = validate_protocol(specification)
    if type(review_wait) is not int or not 0 <= review_wait <= 600:
        raise ValueError("Review wait must be 0..600 seconds")
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError("Benchmark output must be empty to retain earlier evidence")
    write_json(root / "protocol.json", spec)
    training_db = root / "training.sqlite3"
    if baseline_db is not None:
        _backup(baseline_db, training_db)
    else:
        # Initialize through Core, not an invented journal schema.
        _trials(training_db)
    cells = []

    def cell(phase, arm, number, subject, db, frozen=None):
        folder = root / phase / arm / ("challenge_%02d" % number)
        folder.mkdir(parents=True)
        seed = (spec["seed"] + number) % 2**31
        command = [str(python), "-m", "bean.creativity.sketch_lab",
                   "--db", str(db), "--out", str(folder / "attempts"),
                   "--task-ref", "benchmark-%s-%s-%02d" % (phase, arm, number),
                   "--subject", subject, "--memory-mode", arm,
                   "--seed", str(seed), "--attempts", str(spec["attempts"]),
                   "--all-attempts", "--backend", "stdlib", "--require-live"]
        if frozen is not None:
            command += ["--frozen-memory", str(frozen)]
        if review_dir is not None:
            command += ["--review-dir", str(Path(review_dir).resolve()),
                        "--review-wait", str(review_wait)]
        entry = {"phase": phase, "arm": arm, "challenge": number,
                 "subject": subject, "seed": seed, "command": command,
                 "folder": str(folder.relative_to(root)), "returncode": None}
        try:
            completed = runner(command, capture_output=True, text=True,
                               timeout=3600, check=False)
            entry["returncode"] = completed.returncode
            (folder / "stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
            (folder / "stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
        except (OSError, subprocess.TimeoutExpired) as exc:
            entry["error"] = type(exc).__name__ + ": " + str(exc)[:500]
            (folder / "error.txt").write_text(entry["error"] + "\n", encoding="utf-8")
        write_json(folder / "cell.json", entry)
        cells.append(entry)
        return entry

    for number, subject in enumerate(spec["training_subjects"], 1):
        cell("training", "adaptive", number, subject, training_db)
    snapshot = _trials(training_db)
    frozen_path = root / "frozen-memory.json"
    write_json(frozen_path, snapshot)
    dbs = {}
    for arm in ARMS:
        dbs[arm] = root / (arm + ".sqlite3")
        if arm == "none":
            _trials(dbs[arm])
        else:
            _backup(training_db, dbs[arm])
    # Rotate execution order to avoid always giving one arm the earliest
    # provider state. Seeds/budget/subject stay matched within each challenge.
    for number, subject in enumerate(spec["heldout_subjects"], 1):
        offset = (spec["seed"] + number) % len(ARMS)
        for arm in ARMS[offset:] + ARMS[:offset]:
            cell("heldout", arm, number, subject, dbs[arm],
                 frozen_path if arm == "frozen" else None)
    report = {"schema": SCHEMA, "protocol_sha256": spec["protocol_sha256"],
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "frozen_memory_sha256": sha256(frozen_path.read_bytes()).hexdigest(),
              "cells": cells, "separate_process_per_cell": True,
              "learning_improvement_verified": False,
              "weights_updated": False}
    write_json(root / "execution.json", report)
    result = summarize(root)
    write_json(root / "summary.json", result)
    return result


def _review_scores(row, folder):
    feedback = row.get("external_feedback")
    if not isinstance(feedback, dict):
        return None
    if feedback.get("kind") not in ("vision_model", "human"):
        return None
    png_name = row.get("png_file")
    if not isinstance(png_name, str) or Path(png_name).name != png_name:
        return None
    png = folder / png_name
    if png.is_symlink() or not png.is_file():
        return None
    from scripts.build_bean_draw_gallery import _validate_png
    try:
        _validate_png(png.read_bytes())
    except (OSError, ValueError):
        return None
    digest = sha256(png.read_bytes()).hexdigest()
    if row.get("png_sha256") != digest or feedback.get("image_sha256") != digest:
        return None
    from .artifacts import validate_feedback
    try:
        validate_feedback(feedback, png)
    except (TypeError, ValueError, OSError):
        return None
    scores = feedback.get("scores")
    if not isinstance(scores, dict):
        return None
    selected = {}
    for metric in (*METRICS, "diversity"):
        value = scores.get(metric)
        if (type(value) in (int, float) and math.isfinite(value)
                and 0 <= value <= 4):
            selected[metric] = value
    return selected or None


def _verified_run(folder, cell, spec):
    """Verify completed run/sidecar/raw/artifact links before scoring a cell.

    This authenticates matching bytes, not ownership of a provider account or
    the truth of caller supplied metadata. That limitation stays in the report.
    """
    from scripts.build_bean_draw_gallery import _file, _validate_png, validate_svg
    try:
        if cell.get("returncode") != 0:
            raise ValueError("Drawing process did not complete successfully")
        run = json.loads(_file(folder, "run.json").read_bytes())
        if (run.get("schema") != "bean.draw.run.v1"
                or run.get("execution_mode") != "live_model"
                or run.get("provider_kind") not in ("ollama", "openai", "openrouter", "local_llamacpp")
                or not run.get("model_id") or not run.get("run_id")
                or not re.fullmatch(r"[a-f0-9]{40}", run.get("source_git_sha", ""))
                or not run.get("completed_at_utc") or run.get("error")
                or run.get("state") not in ("unverified", "self_reported_satisfactory_unverified",
                                            "host_reported_satisfactory", "host_reported_not_satisfactory")
                or run.get("subject") != cell["subject"]
                or run.get("subject_source") != "human"
                or run.get("memory_mode") != cell["arm"]
                or run.get("seed") != cell["seed"]
                or run.get("attempts") != spec["attempts"]):
            raise ValueError("Incomplete or inconsistent live run provenance")
        calls = _file(folder, "model_calls.json").read_bytes()
        if sha256(calls).hexdigest() != run.get("model_calls_sha256"):
            raise ValueError("Model call archive hash mismatch")
        history = run.get("history")
        if (not isinstance(history, list) or len(history) != spec["attempts"]
                or [x.get("attempt") for x in history] != list(range(1, spec["attempts"] + 1))):
            raise ValueError("Run did not retain the complete matched attempt budget")
        for entry in history:
            name = "attempt_%02d" % entry["attempt"]
            raw = _file(folder, name + ".json").read_bytes()
            row = json.loads(raw)
            if (sha256(raw).hexdigest() != entry.get("metadata_sha256")
                    or Path(entry.get("metadata", "")).name != name + ".json"
                    or row.get("schema") != "bean.draw.attempt.v1"
                    or row.get("attempt") != entry["attempt"]
                    or row.get("verification_state") != "artifacts_verified"
                    or row.get("execution_mode") != "live_model"
                    or any(row.get(key) != run.get(key) for key in
                           ("run_id", "subject", "provider_kind", "model_id", "model_digest",
                            "source_git_sha", "memory_mode", "seed"))):
                raise ValueError("Run does not bind a consistent live attempt sidecar")
            for field, suffix, hash_field in (("svg_file", ".svg", "svg_sha256"),
                                              ("png_file", ".png", "png_sha256"),
                                              ("raw_file", ".raw.json", "raw_sha256")):
                if row.get(field) != name + suffix:
                    raise ValueError("Unexpected artifact filename")
                data = _file(folder, row[field]).read_bytes()
                digest = sha256(data).hexdigest()
                if digest != row.get(hash_field):
                    raise ValueError("Attempt artifact hash mismatch")
                if suffix == ".svg":
                    validate_svg(data)
                    if digest != entry.get("sha256"):
                        raise ValueError("Run SVG hash mismatch")
                elif suffix == ".png":
                    _validate_png(data)
                    if digest != entry.get("png_sha256"):
                        raise ValueError("Run PNG hash mismatch")
        return run, None
    except (ValueError, TypeError, KeyError, OSError, AttributeError) as exc:
        return None, type(exc).__name__ + ": " + str(exc)[:500]


def _mean(values):
    return sum(values) / len(values) if values else None


def _portfolio_diversity(root, arm, outcomes, expected_subjects):
    """Optional joint review of every held-out final image in one arm."""
    path = root / ("portfolio-review." + arm + ".json")
    finals = [x.get("last_png_sha256") for x in outcomes
              if x["phase"] == "heldout" and x["arm"] == arm]
    if len(finals) != expected_subjects or not all(finals) or not path.is_file():
        return None
    if path.stat().st_size > 16000:
        return None
    try:
        report = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(report, dict):
        return None
    score = report.get("diversity")
    if (report.get("schema") != "bean.draw.portfolio_review.v1"
            or report.get("kind") not in ("human", "vision_model")
            or not isinstance(report.get("evaluator"), str) or not report["evaluator"]
            or not isinstance(report.get("feedback"), str) or not report["feedback"]
            or not isinstance(report.get("image_sha256s"), list)
            or any(not isinstance(x, str) for x in report["image_sha256s"])
            or sorted(report["image_sha256s"]) != sorted(finals)
            or type(score) not in (int, float) or not math.isfinite(score)
            or not 0 <= score <= 4):
        return None
    return {"score": score, "evaluator": report["evaluator"],
            "report": path.name, "report_sha256": sha256(path.read_bytes()).hexdigest(),
            "state": "host_reported_joint_pixel_review",
            "independently_authenticated": False}


def summarize(output):
    """Summarize observed external scores, leaving absent evidence null.

    Reports are caller supplied, never independently authenticated here.
    Generalization comparisons concern held-out protocol subjects only.
    """
    root = Path(output)
    spec = validate_protocol(json.loads((root / "protocol.json").read_text()))
    execution = json.loads((root / "execution.json").read_text())
    if execution.get("protocol_sha256") != spec["protocol_sha256"]:
        raise ValueError("Execution and protocol digests differ")
    outcomes, hashes = [], set()
    for cell in execution["cells"]:
        folder = root / cell["folder"] / "attempts"
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError("Cell directory escapes benchmark root")
        verified_run, verification_error = _verified_run(folder, cell, spec)
        attempts, last_png_digest = [], None
        identities = set()
        for sidecar in sorted(folder.glob("attempt_[0-9][0-9].json")):
            row = json.loads(sidecar.read_text())
            if row.get("subject") != cell["subject"]:
                raise ValueError("Drawing subject does not match challenge")
            # Synthetic or unverified execution cannot earn live benchmarks.
            scores = (_review_scores(row, folder) if verified_run is not None else None)
            identities.add((row.get("provider_kind"), row.get("model_id"),
                            row.get("model_digest"), row.get("source_git_sha")))
            if row.get("png_sha256"):
                hashes.add(row["png_sha256"])
            last_png_digest = None
            png_name = row.get("png_file")
            if (verified_run is not None and row.get("execution_mode") == "live_model"
                    and isinstance(png_name, str) and Path(png_name).name == png_name
                    and (folder / png_name).is_file()
                    and sha256((folder / png_name).read_bytes()).hexdigest() == row.get("png_sha256")):
                last_png_digest = row["png_sha256"]
            attempts.append({"attempt": row.get("attempt"),
                             "status": row.get("status"), "scores": scores})
        first = attempts[0].get("scores") if attempts else None
        last = attempts[-1].get("scores") if attempts else None
        delta = {metric: (last[metric] - first[metric]
                         if first and last and metric in first and metric in last
                         else None) for metric in METRICS}
        outcomes.append({"phase": cell["phase"], "arm": cell["arm"],
                         "challenge": cell["challenge"], "subject": cell["subject"],
                         "process_returncode": cell.get("returncode"),
                         "artifact_verification_error": verification_error,
                         "attempts": attempts,
                         "runtime_identity": list(next(iter(identities)))
                         if len(identities) == 1 else None,
                         "last_minus_first_external_score": delta,
                         "last_png_sha256": last_png_digest,
                         "last_scores": last})
    means, iteration = {}, {}
    for arm in ARMS:
        records = [x for x in outcomes if x["phase"] == "heldout" and x["arm"] == arm]
        means[arm] = {metric: _mean([x["last_scores"][metric] for x in records
                                   if x["last_scores"] and metric in x["last_scores"]])
                      for metric in (*METRICS, "diversity")}
        iteration[arm] = {metric: _mean([x["last_minus_first_external_score"][metric]
                                       for x in records
                                       if x["last_minus_first_external_score"][metric] is not None])
                          for metric in METRICS}
    comparisons, matched_counts = {}, {}
    for control in ("frozen", "none"):
        differences = {metric: [] for metric in METRICS}
        for challenge in range(1, len(spec["heldout_subjects"]) + 1):
            paired = {x["arm"]: x for x in outcomes
                      if x["phase"] == "heldout" and x["challenge"] == challenge
                      and x["arm"] in ("adaptive", control)}
            if set(paired) != {"adaptive", control}:
                continue
            adaptive, comparison = paired["adaptive"], paired[control]
            identity = adaptive["runtime_identity"]
            if (not identity or not identity[0] or not identity[1] or not identity[3]
                    or adaptive.get("artifact_verification_error")
                    or comparison.get("artifact_verification_error")
                    or identity != comparison["runtime_identity"]
                    or len(adaptive["attempts"]) != spec["attempts"]
                    or len(comparison["attempts"]) != spec["attempts"]):
                continue
            for metric in METRICS:
                left, right = adaptive["last_scores"], comparison["last_scores"]
                if left and right and metric in left and metric in right:
                    differences[metric].append(left[metric] - right[metric])
        comparisons[control] = {metric: _mean(values)
                                for metric, values in differences.items()}
        matched_counts[control] = {metric: len(values)
                                  for metric, values in differences.items()}
    return {"schema": SCHEMA, "protocol_sha256": spec["protocol_sha256"],
            "subject_source": spec["subject_source"], "outcomes": outcomes,
            "heldout_last_attempt_means": means,
            "iteration_quality_last_minus_first": iteration,
            "generalization_adaptive_minus_control": comparisons,
            "matched_heldout_comparison_counts": matched_counts,
            "portfolio_diversity": {arm: _portfolio_diversity(
                root, arm, outcomes, len(spec["heldout_subjects"])) for arm in ARMS},
            "planned_distinct_heldout_subjects": len(spec["heldout_subjects"]),
            "distinct_recorded_png_hashes": len(hashes),
            "diversity_interpretation": "Per-image diversity ratings are descriptive; portfolio diversity requires a joint review bound to every final PNG; subject/hash counts are mechanics",
            "learning_improvement_verified": False,
            "independent_evaluation_authenticated": False,
            "weights_updated": False,
            "limitations": ["Null scores mean missing legitimate image review, not zero quality",
                            "No broad learning claim from this small challenge set",
                            "Provider determinism and review independence require external verification"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline-db", type=Path)
    parser.add_argument("--review-dir", type=Path)
    parser.add_argument("--review-wait", type=int, default=0)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    result = (summarize(args.out) if args.summarize_only else
              execute(json.loads(args.protocol.read_text()), args.out,
                      baseline_db=args.baseline_db, review_dir=args.review_dir,
                      review_wait=args.review_wait))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

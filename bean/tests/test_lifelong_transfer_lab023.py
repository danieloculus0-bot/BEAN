"""Credential-free Lab023 contract tests, using explicitly named fake model writers."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pytest

from bean.evaluation.lifelong_transfer_lab023 import learn, transfer, judge, reflect
from bean.evaluation.transfer_tasks import TASKS
from bean.optimization.autodev import Journal
from experiments.agent_arena.author import MODEL, sha
from experiments.agent_arena.cases import CASES


def create_training(folder):
    proposals = folder / "initial"
    proposals.mkdir()
    receipts = []
    scores = []
    for task in TASKS:
        source = task.original + "\n# Synthetic training candidate for harness\n"
        (proposals / (task.task_id + ".py")).write_text(source)
        receipts.append({
            "task_id": task.task_id, "provider_status": "proposal_generated",
            "model_requested": "openrouter/free", "source_sha256": sha(source),
        })
        scores.append({
            "task_id": task.task_id, "status": "evaluated",
            "passed": 24, "total": 60,
        })
    (proposals / "receipt.json").write_text(json.dumps({
        "schema": "bean.autonomy.lab021.generation.v1",
        "tasks": receipts,
    }))
    grades = folder / "dev.json"
    grades.write_text(json.dumps({
        "schema": "bean.autonomy.lab021.evaluation.v1",
        "phase": "development", "tasks": scores,
    }))
    return proposals, grades


def fake_reflection(task, source, score, key):
    assert source.startswith(task.original)
    assert score["passed"] == 24
    return {"lesson": "Validate edge cases and independent ordering assumptions.",
            "model_served": MODEL}


def fake_author(spec, key):
    assert "test" not in spec
    assert key == "mock-not-a-key"
    retained = "UNTRUSTED MEMORY" in spec["prompt"]
    candidate = spec["source"] + ("\n# retained\n" if retained else "\n# cold\n")
    return ({
        "status": "candidate_drafted_not_tested",
        "model_requested": MODEL,
        "model_served": [MODEL],
        "candidate_sha256": sha(candidate),
    }, candidate)


def fake_grader(source, tests):
    if "# retained" in source:
        n = 7
    elif "# cold" in source:
        n = 3
    else:
        n = 1
    return {"status": "passed" if n == 8 else "failed",
            "passed_tests": n, "total_tests": 8}


def ready_state(tmp_path):
    proposals, scores = create_training(tmp_path)
    state = tmp_path / "journal.sqlite"
    report = learn(proposals, scores, state, tmp_path / "learning.json",
                   api_key="mock-not-a-key", reflector=fake_reflection)
    return state, report


def test_fully_causal_fake_pipeline_and_actual_sqlite_reopen(tmp_path):
    state, report = ready_state(tmp_path)
    assert report["model_authored_lessons"] == len(TASKS)
    assert report["restart_verified"]
    journal = Journal(state)
    tip = journal.export()["tip"]
    journal.close()
    root = tmp_path / "authored"
    document = transfer(state, root, api_key="mock-not-a-key",
                        author=fake_author)
    assert document["journal_tip"] == tip
    assert document["candidates_tested_by_author"] is False
    for name in CASES:
        assert document["cases"][name]["cold"]["public_source_sha256"] == (
            document["cases"][name]["retained"]["public_source_sha256"])
    verdict = judge(root, state, tmp_path / "verdict.json", grader=fake_grader)
    assert verdict["classification"] == "POSITIVE_CAUSAL_RETENTION_PILOT"
    assert verdict["total_retained_passed"] > verdict["total_cold_passed"]
    assert verdict["journal_restart_verified"]
    assert json.loads((tmp_path / "verdict.json").read_text()) == verdict


def test_missing_reflections_cannot_claim_learning(tmp_path):
    proposals, scores = create_training(tmp_path)
    state = tmp_path / "missing.sqlite"
    report = learn(proposals, scores, state, tmp_path / "out.json",
                   api_key="", reflector=lambda *args: None)
    assert report["model_authored_lessons"] == 0
    with pytest.raises(ValueError, match="fewer than two"):
        transfer(state, tmp_path / "authored", api_key="mock-not-a-key",
                 author=fake_author)


def test_training_cannot_ingest_changed_model_output(tmp_path):
    proposals, scores = create_training(tmp_path)
    (proposals / "intervals.py").write_text("secret altered source")
    with pytest.raises(ValueError, match="training source hash"):
        learn(proposals, scores, tmp_path / "db.sqlite", tmp_path / "out.json",
              api_key="mock-not-a-key", reflector=fake_reflection)


def test_holdout_scores_refused_as_training_data(tmp_path):
    proposals, scores = create_training(tmp_path)
    data = json.loads(scores.read_text())
    data["phase"] = "holdout"
    scores.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="development"):
        learn(proposals, scores, tmp_path / "db.sqlite", tmp_path / "out.json",
              api_key="mock-not-a-key", reflector=fake_reflection)


def test_journal_tampering_detected_after_restart(tmp_path):
    state, _ = ready_state(tmp_path)
    import sqlite3
    with sqlite3.connect(state) as db:
        db.execute("UPDATE attempts SET payload='{}' WHERE id=1")
    with pytest.raises(ValueError, match="altered or discontinuous"):
        transfer(state, tmp_path / "out", api_key="mock-not-a-key",
                 author=fake_author)


def test_model_candidate_tampering_is_fatal(tmp_path):
    state, _ = ready_state(tmp_path)
    root = tmp_path / "authored"
    transfer(state, root, api_key="mock-not-a-key", author=fake_author)
    first = next(iter(CASES))
    (root / "candidates" / first / "retained.py").write_text("def backdoor(): pass")
    with pytest.raises(ValueError, match="tampered candidate"):
        judge(root, state, tmp_path / "verdict.json", grader=fake_grader)


def test_missing_model_candidate_cannot_be_reported_as_success(tmp_path):
    state, _ = ready_state(tmp_path)
    def missing(spec, key):
        return ({
            "status": "provider_failure",
            "model_requested": MODEL,
            "model_served": [],
        }, None)
    root = tmp_path / "authored"
    transfer(state, root, api_key="mock-not-a-key", author=missing)
    verdict = judge(root, state, tmp_path / "verdict.json", grader=fake_grader)
    assert verdict["classification"] == "INCONCLUSIVE"
    assert not verdict["all_candidates_submitted"]


def test_changed_provider_invalidates_same_model_comparison(tmp_path):
    state, _ = ready_state(tmp_path)
    def split_provider(spec, key):
        rec, candidate = fake_author(spec, key)
        if "UNTRUSTED MEMORY" in spec["prompt"]:
            rec["model_served"] = ["other-provider-model"]
        return rec, candidate
    root = tmp_path / "authored"
    transfer(state, root, api_key="mock-not-a-key", author=split_provider)
    result = judge(root, state, tmp_path / "result.json", grader=fake_grader)
    assert result["classification"] == "INCONCLUSIVE"


def test_reflect_fails_closed_without_api_key():
    assert reflect(TASKS[0], TASKS[0].original, {"passed": 0, "total": 50}, "") is None

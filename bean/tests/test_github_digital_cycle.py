"""End-to-end synthetic scoring on BEAN's existing persistent reasoning journal."""
from __future__ import annotations

import json
import sqlite3

import pytest

from bean.evaluation.active_abstraction_benchmark import World
from bean.evaluation.github_digital_cycle import (
    FAMILIES, BLIND, _hash, run_scored_digital_cycle,
)
from bean.learning.reasoning_service import NativeReasoningService
from scripts.invoke_bean import checkpoint, unpack


def _evaluations(path):
    service = NativeReasoningService(path, model=None)
    try:
        return [
            item["data"] for item in service.bank.journal.events()
            if item["kind"] == "trial" and item["data"].get("experiment") ==
            "bean.github.digital_feedback.v1"
        ]
    finally:
        service.close()


def test_actual_feedback_blind_controls_and_durable_restart(tmp_path):
    db = tmp_path / "reasoning.sqlite3"
    first = run_scored_digital_cycle(
        db, generation=1, source_sha="local-validation")
    assert first["new_evaluation"] is True
    assert first["blind_cases_total"] == 3 * len(BLIND)
    assert set(first["families"]) == set(FAMILIES)

    records = _evaluations(db)  # brand-new service and SQLite connection
    assert len(records) == len(FAMILIES)
    assert sum(row["correct"]["candidate"] for row in records) == (
        first["candidate_correct_total"])
    for record in records:
        assert record["learning_reward_calls"] == 60
        assert record["passive_reward_calls"] == 60
        assert record["shuffled_reward_calls"] == 60
        assert len(record["case_level_evidence"]) == len(BLIND)
        assert record["benchmark_is_synthetic_public_fixture"] is True
        assert record["external_independent_verification"] is False
        assert record["heldout_evaluated_after_service_restart"] is True
        assert record["model_weights_trained"] is False
        unsigned = {k: v for k, v in record.items()
                    if k != "evaluation_sha256"}
        assert record["evaluation_sha256"] == _hash(unsigned)
        world = World(record["world_id"], record["family"])
        for case in record["case_level_evidence"]:
            assert case["truth"] == world.correct_action(case["case_id"])
            assert case["sensors_sha256"] == _hash(
                world.observe(case["case_id"]))
            for arm, action in case["actions"].items():
                assert case["correct"][arm] == (action == case["truth"])
    # Duplicate generation must never add a second scored receipt.
    duplicate = run_scored_digital_cycle(
        db, generation=1, source_sha="local-validation")
    assert duplicate["new_evaluation"] is False
    assert duplicate["source_evidence_sha256"] == first["source_evidence_sha256"]
    assert len(_evaluations(db)) == len(FAMILIES)

    second = run_scored_digital_cycle(
        db, generation=2, source_sha="local-validation")
    assert second["new_evaluation"] is True
    assert second["blind_cases_total"] == first["blind_cases_total"]
    rows = _evaluations(db)
    assert len(rows) == 2 * len(FAMILIES)
    assert all(r["prior_generation_transfer_correct"] is not None
               for r in rows if r["generation"] == 2)


def test_existing_checkpoint_roundtrip_preserves_scored_rules(tmp_path):
    # The new evaluator lives in the same real reasoning SQLite file that
    # invoke_bean.checkpoint() already snapshots and signs.
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    core = runtime / "bean_memory.sqlite3"
    with sqlite3.connect(core) as db:
        db.execute("CREATE TABLE synthetic (value TEXT)")
        db.execute("INSERT INTO synthetic VALUES ('no private data')")
    reasoning = runtime / "bean_reasoning.sqlite3"
    scored = run_scored_digital_cycle(
        reasoning, generation=1, source_sha="local-validation")
    archive = tmp_path / "state"
    receipt = checkpoint(
        archive, runtime, None, 1, 10, 2, 12,
        digital_learning=scored)
    assert receipt["digital_learning"]["source_evidence_sha256"] == (
        scored["source_evidence_sha256"])

    restored = tmp_path / "restarted"
    restored.mkdir()
    assert unpack(archive, restored)["receipt_sha256"] == (
        receipt["receipt_sha256"])
    after = _evaluations(restored / "bean_reasoning.sqlite3")
    assert len(after) == len(FAMILIES)
    assert {r["evaluation_sha256"] for r in after} == {
        record["evaluation_sha256"] for record in _evaluations(reasoning)}
    assert all("case_level_evidence" in item for item in after)


def test_invalid_or_conflicting_generation_never_earns_credit(tmp_path):
    db = tmp_path / "reasoning.sqlite3"
    with pytest.raises(ValueError, match="generation"):
        run_scored_digital_cycle(db, generation=0)
    assert not db.exists()
    run_scored_digital_cycle(db, generation=1, source_sha="local-validation")
    with pytest.raises(ValueError, match="revision conflict"):
        run_scored_digital_cycle(db, generation=1, source_sha="a" * 40)
    assert len(_evaluations(db)) == len(FAMILIES)

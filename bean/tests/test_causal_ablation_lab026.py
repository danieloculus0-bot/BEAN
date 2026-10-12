"""Contract tests for Lab026. All model responses in this file are MOCKS.

Passing these tests proves the experiment's controls/receipts, not intelligence.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from bean.evaluation import causal_ablation_lab026 as lab
from bean.evaluation.transfer_tasks import TASKS
from bean.optimization.autodev import Journal
from experiments.agent_arena.author import sha
from experiments.agent_arena.cases import CASES

ROUTE = "ollama/qwen2.5-coder:0.5b"


def journal_file(tmp_path):
    path = tmp_path / "memory.sqlite"
    store = Journal(path)
    try:
        for i, task in enumerate(TASKS):
            store.append({
                "objective": task.task_id,
                "iteration": 0,
                "outcome": "evaluated",
                "train_passed": (20, 80, 40)[i],
                "train_total": 100,
                "source_sha256": sha(task.original),
                "lesson": ("Check boundary conditions before changing source.",
                           "Make graph traversal stable under cycles.",
                           "Verify inputs and duplicate record IDs.")[i],
                "reflection_model": ROUTE,
                "training_model_requested": ROUTE,
                "training_model_served": ROUTE,
                "train_phase": "development",
            })
    finally:
        store.close()
    return path


def mock_writer(spec, _key):
    # This fake returns unchanged source deliberately; it is NOT learning.
    source = spec["source"]
    return ({
        "status": "candidate_drafted_not_tested",
        "candidate_sha256": sha(source),
        "model_requested": ROUTE,
        "model_served": [ROUTE],
        "attempts": [{"number": 1, "status": "mock"}],
    }, source)


def fake_grader(source, suite):
    # Fixed score for every arm: no arm gets credit for the fake.
    return {"status": "failed", "passed_tests": 2, "total_tests": 10}


def test_real_bean_sqlite_journal_restarts_and_controls_have_distinct_context(tmp_path):
    state = journal_file(tmp_path)
    notes, tip = lab.contexts_from_journal(state, ROUTE)
    assert set(notes) == set(lab.ARMS)
    assert notes["cold"] == ""
    assert "boundary conditions" in notes["simple_history"]
    assert "graph traversal" in notes["bean_evidence"]
    assert "source " in notes["bean_evidence"]
    assert "boundary conditions" not in notes["bean_evidence"]
    assert "graph traversal" not in notes["placebo"]
    assert len(notes["placebo"]) > 20
    assert tip != "GENESIS"
    with pytest.raises(ValueError, match="training model differs"):
        lab.contexts_from_journal(state, "ollama/other:tag")


def test_four_arm_counterbalance_repeats_each_ordinal_position():
    for case_index in (0, 1):
        rounds = [lab.arm_order(trial, case_index) for trial in range(4)]
        assert all(set(row) == set(lab.ARMS) for row in rounds)
        for arm in lab.ARMS:
            assert sorted(row.index(arm) for row in rounds) == [0, 1, 2, 3]


def test_author_does_not_run_fabricated_model_code_or_hidden_tests(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"
    prompts = []

    def writer(spec, key):
        assert key == ""
        prompts.append(spec["prompt"])
        assert CASES[spec["name"]]["test"] not in spec["prompt"]
        return mock_writer(spec, key)

    result = lab.author_candidates(state, out, model_requested=ROUTE,
                                   writer=writer, trials=1)
    assert result["candidate_source_executed_by_author"] is False
    assert len(result["calls"]) == len(CASES) * 4
    assert len(prompts) == len(CASES) * 4
    assert not (out / "verdict.json").exists()


def test_one_trial_is_inconclusive_even_if_mock_source_is_consistent(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"
    lab.author_candidates(state, out, model_requested=ROUTE,
                          writer=mock_writer, trials=1)
    verdict = lab.independent_judge(out, state, tmp_path / "verdict.json",
                                    grader=fake_grader)
    assert verdict["classification"] == "INCONCLUSIVE"
    assert verdict["complete"] is True
    assert verdict["same_model_verified"] is True
    assert all(score == 0.2 for score in verdict["averages"].values())
    assert verdict["evidence_sha256"]
    assert all(not x.startswith("PILOT_SIGNAL") for x in
               [verdict["classification"]])


def test_four_trials_with_no_benefit_report_no_advantage(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"
    lab.author_candidates(state, out, model_requested=ROUTE,
                          writer=mock_writer, trials=4)
    verdict = lab.independent_judge(out, state, tmp_path / "verdict.json",
                                    grader=fake_grader)
    assert verdict["classification"] == "NO_ADVANTAGE_DEMONSTRATED"
    assert verdict["expected_per_arm"] == len(CASES) * 4
    assert len(verdict["improvement_targets"]) >= 3


def test_missing_candidates_are_inconclusive_not_beans_victory(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"

    def unavailable(spec, key):
        return ({"status": "provider_failure",
                 "model_requested": ROUTE,
                 "model_served": [],
                 "attempts": [{"reason": "unavailable"}]}, None)

    lab.author_candidates(state, out, model_requested=ROUTE,
                          writer=unavailable, trials=4)
    verdict = lab.independent_judge(out, state, tmp_path / "verdict.json",
                                    grader=fake_grader)
    assert verdict["classification"] == "INCONCLUSIVE"
    assert verdict["complete"] is False
    assert verdict["same_model_verified"] is False
    assert verdict["evaluated_per_arm"] == {a: 0 for a in lab.ARMS}


def test_candidate_hash_tamper_is_rejected(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"
    lab.author_candidates(state, out, model_requested=ROUTE,
                          writer=mock_writer)
    path = next((out / "candidates").rglob("*.py"))
    path.write_text("raise RuntimeError('tampered')", encoding="utf-8")
    with pytest.raises(ValueError, match="modified candidate"):
        lab.independent_judge(out, state, tmp_path / "bad.json", grader=fake_grader)


def test_manifest_cannot_swap_arm_context_or_model(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"
    lab.author_candidates(state, out, model_requested=ROUTE,
                          writer=mock_writer)
    path = out / "manifest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    first = next(iter(doc["calls"]))
    doc["calls"][first]["note_sha256"] = "a" * 64
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        lab.independent_judge(out, state, tmp_path / "bad.json", grader=fake_grader)


def test_reused_author_directory_rejected(tmp_path):
    state = journal_file(tmp_path)
    out = tmp_path / "authors"
    lab.author_candidates(state, out, model_requested=ROUTE,
                          writer=mock_writer)
    with pytest.raises(ValueError, match="new empty"):
        lab.author_candidates(state, out, model_requested=ROUTE,
                              writer=mock_writer)


def test_synthetic_positive_is_only_preliminary_pilot_not_learning_proof():
    cases = {
        name: {
            str(t): {
                arm: {"status": "evaluated", "total_tests": 10,
                      "passed_tests": (7 if arm == "bean_evidence" else 3)}
                for arm in lab.ARMS
            } for t in range(4)
        } for name in CASES
    }
    report = lab.compare_scores(cases, 4)
    assert report["classification"] == "PRELIMINARY_PILOT_SIGNAL"
    assert report["averages"]["bean_evidence"] == 0.7
    assert "learning" not in report["classification"].lower()


def test_alternating_wins_cannot_masquerade_as_consistent_learning():
    """Pooled gains over all three controls must not hide round regressions."""
    cases = {
        name: {
            str(t): {
                arm: {
                    "status": "evaluated", "total_tests": 10,
                    "passed_tests": (
                        (8 if t % 2 == 0 else 2)
                        if arm == "bean_evidence" else 3
                    ),
                }
                for arm in lab.ARMS
            }
            for t in range(4)
        }
        for name in CASES
    }
    report = lab.compare_scores(cases, 4)
    assert report["averages"]["bean_evidence"] > report["averages"]["cold"]
    assert report["averages"]["bean_evidence"] > report["averages"]["simple_history"]
    assert report["averages"]["bean_evidence"] > report["averages"]["placebo"]
    assert report["strict_taskwise_round_wins"] == [True, False, True, False]
    assert report["longest_strict_taskwise_streak"] == 1
    assert report["classification"] == "NO_ADVANTAGE_DEMONSTRATED"


def test_three_consecutive_wins_still_only_make_preliminary_pilot():
    cases = {
        name: {
            str(t): {
                arm: {"status": "evaluated", "total_tests": 10,
                      "passed_tests": (
                          (7 if t < 3 else 2) if arm == "bean_evidence" else 3
                      )}
                for arm in lab.ARMS
            } for t in range(4)
        } for name in CASES
    }
    report = lab.compare_scores(cases, 4)
    assert report["strict_taskwise_round_wins"] == [True, True, True, False]
    assert report["longest_strict_taskwise_streak"] == 3
    assert report["classification"] == "PRELIMINARY_PILOT_SIGNAL"


def test_no_cases_never_proves_learning():
    report = lab.compare_scores({}, 4)
    assert report["classification"] == "INCONCLUSIVE"
    assert report["complete"] is False
    assert report["longest_strict_taskwise_streak"] == 0

"""Lab 018 falsification tests: time series, symmetric inputs and dissent."""
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from bean.evaluation.triad_lab018 import (
    FEATURES, ROUNDS, TRAIN_N, TEST_N, Learner, PRIORS, claim,
    make_cases, peer_distinctions, run, score, visible,
)


def test_all_paths_get_identical_evidence_budget_and_rotating_roles():
    report = run()
    assert report["schema"] == "bean.triad-learning.lab018.v1"
    assert report["equal_feedback_budget_per_peer"] == TRAIN_N * (ROUNDS - 1)
    assert len(report["rounds"]) == ROUNDS
    assert report["fixed_panel_never_used_for_training"]
    assert report["train_test_disjoint"]
    panels = {record["same_fixed_panel_sha256"] for record in report["rounds"]}
    assert len(panels) == 1, "The repeated benchmark silently changed"
    assert len({record["fresh_panel_sha256"] for record in report["rounds"]}) == ROUNDS
    for idx, record in enumerate(report["rounds"]):
        assert sorted(record["roles"]) == ["A", "B", "C"]
        assert set(record["roles"].values()) == {"selector", "builder", "skeptic"}
        assert record["training_cases_seen_before_test"] == TRAIN_N * idx
        assert all(record["scores"][name]["learning_steps_completed"] == idx
                   for name in ("A", "B", "C"))
        assert len(record["claims"]) == 3 * 5
    assert [report["rounds"][i]["roles"]["A"] for i in range(3)] == [
        "selector", "builder", "skeptic"
    ]


def test_every_path_makes_support_contradiction_and_complementary_check():
    report = run()
    for record in report["rounds"]:
        for case_id in {c["case_id"] for c in record["claims"]}:
            claims = [c for c in record["claims"] if c["case_id"] == case_id]
            assert len(claims) == 3
            assert {c["peer"] for c in claims} == {"A", "B", "C"}
            for c in claims:
                assert c["claim"] in ("improvement_likely", "regression_likely")
                assert c["counterclaim"] == (
                    "regression_possible" if c["claim"] == "improvement_likely"
                    else "improvement_possible")
                assert c["complementary_check"].startswith("Independent test of")
                assert not c["verified_fact"]
                assert c["test_result_status"] == "not_run"


def test_genuine_behavioral_distinction_is_measured_not_assumed():
    report = run()
    for round_ in report["rounds"]:
        disagreement = round_["distinction"]["disagreement_rate"]
        assert 0 <= disagreement <= 1
        assert 0 <= round_["distinction"]["unanimous_wrong_rate"] <= 1
        for count in round_["distinction"]["unique_correct_dissent"].values():
            assert isinstance(count, int) and 0 <= count <= TEST_N
    assert any(r["distinction"]["disagreement_rate"] > 0 for r in report["rounds"]), (
        "All three synthetic peers happened to be indistinguishable"
    )
    # Distinct opinions may still be wrong; we must retain unanimous failure.
    assert "unanimous_wrong_rate" in report["rounds"][-1]["distinction"]


def test_iterative_learning_changed_actual_parameters_but_no_success_is_fabricated():
    report = run()
    for name in "ABC":
        initial = report["rounds"][0]["scores"][name]
        latest = report["rounds"][-1]["scores"][name]
        assert initial["learning_steps_completed"] == 0
        assert latest["learning_steps_completed"] == ROUNDS - 1
        assert any(abs(v) > 0.00001
                   for v in report["learned_vs_frozen_summary"][name]["weight_change"])
        assert initial["frozen_fixed"] == latest["frozen_fixed"]
        assert latest["frozen_fresh"]["n"] == TEST_N
        assert latest["fresh"]["n"] == TEST_N
        assert -1 <= report["learned_vs_frozen_summary"][name][
            "last_fresh_vs_frozen_accuracy"] <= 1
    # A result may be a regression. We must never test "it always improves".
    assert report["no_self_approval"] is True
    assert report["distinct_claims_not_distinct_ai_models"] is True


def test_evaluator_truth_and_shift_are_unavailable_to_peer():
    row = make_cases("EVALUATOR_ONLY", 0, 1, shift=True)[0]
    assert set(visible(row)) == {"case_id", "features"}
    agent = Learner("A", list(PRIORS[0]))
    with pytest.raises(ValueError, match="leaked"):
        agent.probability(row)
    assert 0 <= agent.probability(visible(row)) <= 1


def test_learning_never_inspects_fixed_or_fresh_test_panels(monkeypatch):
    import bean.evaluation.triad_lab018 as lab
    seen = []
    original = lab.Learner.learn

    def guard(self, training, **kwargs):
        seen.extend(t["case_id"] for t in training)
        assert all(t["case_id"].startswith("TRAIN_ONLY:") for t in training)
        return original(self, training, **kwargs)

    monkeypatch.setattr(lab.Learner, "learn", guard)
    record = lab.run()
    assert len(seen) == 3 * TRAIN_N * (ROUNDS - 1)
    assert not any("FRESH_NEVER_TRAIN" in key or "FIXED_NEVER_TRAIN" in key
                   for key in seen)
    assert record["train_test_disjoint"]


def test_repeated_experiment_and_receipts_are_deterministic():
    a = run()
    b = run()
    assert a == b
    assert json.dumps(a, allow_nan=False)
    assert all(0 <= val["accuracy"] <= 1
               for it in a["rounds"] for item in it["scores"].values()
               for key, val in item.items() if key in
               ("fixed", "fresh", "frozen_fixed", "frozen_fresh"))


def _import_exact(name, path):
    p = Path(path)
    if not p.is_file():
        raise AssertionError(f"pinned external checkout missing: {p}")
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_live_repository_three_path_handoff_contract():
    selector_path = os.environ.get("TRIAD_SELECTOR_MODULE")
    builder_path = os.environ.get("TRIAD_BUILDER_MODULE")
    if not selector_path and not builder_path:
        pytest.skip("standalone local test; pinned multi-branch checkouts run in peer CI")
    assert selector_path and builder_path, "must supply both independent source paths"
    selector = _import_exact("triad_pinned_selector", selector_path)
    builder = _import_exact("triad_pinned_builder", builder_path)
    # Actual path A ranks an evidenced candidate. Actual path B prepares a
    # code change (not executed). Path C evaluates both contracts independently.
    opp = selector.ImprovementOpportunity(
        "fixture-repair", "Correct a reproducible offline regression",
        ("test:verified:12",), 3, 5, .83, 1, True)
    ranks = selector.rank_improvements([opp])
    assert [r.opportunity.identifier for r in ranks] == ["fixture-repair"]
    source = "def answer():\n    return 0\n"
    candidate = builder.draft_candidate(
        source=source,
        base_commit="a772c41db9b38580c1532565086a071f82dc02a0",
        path="bean/evaluation/fixture.py",
        problem="Correct a seeded regression confirmed by independent test",
        proposer=lambda problem, old: old.replace("return 0", "return 1"),
    )
    diff = candidate.preview(source)
    assert "+    return 1" in diff and "-    return 0" in diff
    assert "return 0" in source
    assert len(candidate.candidate_digest) == 64
    assert not hasattr(candidate, "merge")

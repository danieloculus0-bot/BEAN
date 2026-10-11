"""Lab 013: benchmark correctness, isolation, ablation and drift tests."""
import json

import pytest

from bean.evaluation.composite_growth import (
    AdaptivePolicy, Decision, Episode, FrozenPolicy, Memory, Observation,
    SOURCES, TEST_DOMAINS, TRAIN_DOMAINS, make_cases, run_suite, score,
    summary, trial,
)
from bean.memory.store import get_store, init_store


def test_fixtures_are_reproducible_with_same_seed():
    first = make_cases(13, 100, "training")
    assert first == make_cases(13, 100, "training")
    assert first != make_cases(17, 100, "training")


def test_train_and_holdout_domains_are_disjoint():
    assert not set(TRAIN_DOMAINS) & set(TEST_DOMAINS)
    train = make_cases(19, 50, "training")
    test = make_cases(19, 50, "holdout")
    assert {e.domain for e in train} == set(TRAIN_DOMAINS)
    assert {e.domain for e in test} == set(TEST_DOMAINS)
    assert {o.ref for e in train for o in e.records}.isdisjoint(
        {o.ref for e in test for o in e.records}
    )


def test_truth_is_not_a_field_of_observation():
    episode = make_cases(11, 10, "training")[2]
    assert episode.truth in (0, 1)
    assert not hasattr(episode.records[0], "truth")


def test_missing_is_unknown_not_zero():
    episode = Episode("quality", 0, (), "missing")
    decision = FrozenPolicy().choose(episode.records)
    assert decision.answer is None
    result = score(episode, decision)
    assert result["correct"] == 0
    assert result["unknown"] == 1
    assert result["evidence_ok"] == 1


def test_verified_zero_equivalent_is_a_real_reading_not_missing():
    o = Observation("synthetic-zero", "dashboard", 0)
    decision = FrozenPolicy().choose((o,))
    assert decision.answer == 0
    assert score(Episode("energy",0,(o,),"routine"),decision)["correct"] == 1


def test_stale_only_record_does_not_get_promoted():
    o = Observation("old-scan","inspector",1,"stale")
    assert FrozenPolicy().choose((o,)).answer is None


def test_conflict_cases_exist_without_true_answer_leakage():
    cases = make_cases(19, 100, "training")
    assert any(x.kind == "conflict" for x in cases)
    assert any(x.kind == "missing" for x in cases)
    assert any(x.kind == "stale" for x in cases)


def test_forged_citation_fails_provenance_even_if_answer_correct():
    o = Observation("source-a","inspector",1)
    episode = Episode("energy",1,(o,),"routine")
    result = score(episode,Decision(1,0.9,"imaginary-reference"))
    assert result["correct"] == 1
    assert result["evidence_ok"] == 0


def test_fabricated_verified_state_is_detected():
    o = Observation("r","inspector",1)
    event = Episode("energy",1,(o,),"routine")
    fabricated = Decision(1,0.9,"r",epistemic_status="verified")
    assert score(event,fabricated)["fabricated_verified"] == 1


def test_feedback_trains_only_in_explicit_training_call(tmp_path):
    init_store(str(tmp_path/"feedback.sqlite"))
    memory = Memory()
    episode = Episode(
        "fabrication",1,(Observation("a","dashboard",0),
                         Observation("b","inspector",1)),"conflict"
    )
    assert memory.count() == 0
    Memory().learn_supervised(episode)
    assert memory.count() == 2
    assert memory.posterior("dashboard")[0] < 2/3
    assert memory.posterior("inspector")[0] > 2/3
    assert memory.posterior("inspector")[1] == 1


def test_feedback_history_bounded_to_recent_48(tmp_path):
    init_store(str(tmp_path/"history.sqlite"))
    memory = Memory()
    for idx in range(65):
        memory.learn_supervised(Episode(
            "cooling",1,(Observation(str(idx),"inspector",1),),"routine"
        ))
    assert memory.count() == 65
    reliability,n = memory.posterior("inspector")
    assert n == 48
    assert reliability > 0.95


def test_adaptive_prefers_source_with_evidence_of_reliability(tmp_path):
    init_store(str(tmp_path/"ranking.sqlite"))
    memory = Memory()
    for i in range(25):
        memory.learn_supervised(Episode(
            "fabrication",1,(Observation(f"d{i}","dashboard",0),
                             Observation(f"v{i}","telemetry",1)),"conflict"
        ))
    choice = AdaptivePolicy(memory).choose(
        (Observation("live-dashboard","dashboard",0),
         Observation("live-telemetry","telemetry",1))
    )
    assert choice.answer == 1
    assert choice.source_ref == "live-telemetry"
    assert choice.epistemic_status == "inference"


def test_single_seed_retention_scheduler_and_guard():
    result = trial(23,training=100,holdout=90)
    assert result["retention_roundtrip"]
    assert result["scheduler_checks"] > 0
    assert result["scheduler_ok"]
    assert result["holdout_feedback_writes"] == 0
    assert result["external_actions"] == 0
    assert result["world_memory_promotions"] == 0
    assert result["guard_denials"] == 0
    assert result["adaptive_holdout"]["provenance_rate"] == 1
    assert result["adaptive_holdout"]["fabricated_verified_claims"] == 0


def test_trials_reproducible_without_random_global_state():
    assert trial(11,training=60,holdout=60) == trial(11,training=60,holdout=60)


def test_paired_experiment_improves_narrow_calibration_not_llm():
    report = run_suite(seeds=(11,23,37),training=120,holdout=90)
    assert report["adaptive_component"] == "supervised_source_reliability_only"
    assert not report["independent_general_learning_proven"]
    assert not report["model_weights_updated"]
    assert report["aggregate"]["normal_positive_seeds"] >= 2
    assert report["aggregate"]["normal_mean_paired_gain"] > 0
    assert report["aggregate"]["restart_retention_passed"]
    assert report["aggregate"]["scheduler_checks_passed"]
    assert report["aggregate"]["provenance_passed"]
    assert report["aggregate"]["guard_denials"] == 0
    assert report["aggregate"]["holdout_feedback_writes"] == 0
    assert report["mock_reasoning_baseline"]["holdout"]["passed"] == 0
    assert report["mock_reasoning_baseline"]["holdout"]["total"] == 4


def test_drift_trial_is_heldout_and_does_not_retrain():
    normal = trial(41,training=120,holdout=120)
    drift = trial(41,training=120,holdout=120,drift=True)
    assert normal["source_calibration"] == drift["source_calibration"]
    assert normal["feedback_rows"] == drift["feedback_rows"]
    assert drift["holdout_feedback_writes"] == 0
    assert normal["control_holdout"] != drift["control_holdout"] or (
        normal["adaptive_holdout"] != drift["adaptive_holdout"]
    )
    assert normal["scheduler_ok"] and drift["scheduler_ok"]


def test_absent_and_stale_do_not_count_as_correct_answers_in_suite():
    result = trial(17,training=120,holdout=90)
    holdout = result["adaptive_holdout"]
    assert holdout["unknown"] > 0
    assert holdout["correct"]+holdout["wrong"]+holdout["unknown"] == holdout["cases"]


def test_invalid_small_experiment_rejected():
    with pytest.raises(ValueError):
        trial(1,training=2,holdout=20)
    with pytest.raises(ValueError):
        run_suite(seeds=(11,11),training=50,holdout=50)
    with pytest.raises(ValueError):
        make_cases(1,10,"answer_key")

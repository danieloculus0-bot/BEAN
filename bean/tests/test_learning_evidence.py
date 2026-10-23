"""Synthetic-only validation of BEAN learning history and matched controls."""
import json
import sqlite3

import pytest

from bean.evaluation.learning_evidence import (
    GENESIS, LearningEvidenceLedger, TrialMeasurement, assess_matched_trials,
)


def ledger():
    return LearningEvidenceLedger(sqlite3.connect(":memory:"))


def sample(arm, replicate=0, *, score=0.5, latency_ms=8.0, **kwargs):
    data = {
        "arm": arm, "task_id": "task-alpha", "replicate": replicate,
        "model_id": "qwen-local", "model_revision": "sha:1234",
        "document_sha256": "a" * 64, "protocol_sha256": "b" * 64,
        "budget_tokens": 250, "scorer_ref": "independent:judge",
        "run_ref": f"run-{replicate}-{arm}", "score": score,
        "latency_ms": latency_ms,
    }
    data.update(kwargs)
    return TrialMeasurement(**data)


def test_append_read_and_chain():
    l = ledger()
    assert l.verify_chain() == GENESIS
    a = l.append(event_id="evt-1", claim_id="H1", stage="observation",
                 source_ref="meter:abc", payload={"reading": 1, "units": "s"})
    b = l.append(event_id="evt-2", claim_id="H1", stage="hypothesis",
                 source_ref="hypothesis:abc", payload={"prediction": "slower"})
    assert a["new"] and b["new"] and len(b["hash"]) == 64
    assert [x["stage"] for x in l.history("H1")] == ["observation", "hypothesis"]
    assert l.verify_chain() == b["hash"]


def test_idempotent_replay_but_collision_fails():
    l = ledger()
    arg = dict(event_id="same", claim_id="C", stage="observation",
               source_ref="fixture:1", payload={"fact": "A"})
    first = l.append(**arg)
    assert not l.append(**arg)["new"]
    with pytest.raises(ValueError, match="collision"):
        l.append(**{**arg, "payload": {"fact": "B"}})
    assert l.verify_chain() == first["hash"]


def test_restart_persists_and_replays(tmp_path):
    file = str(tmp_path / "learning.db")
    db = sqlite3.connect(file)
    l = LearningEvidenceLedger(db)
    l.append(event_id="e", claim_id="P", stage="reflection",
             source_ref="run:77", payload={"lesson": "restart"})
    tip = l.verify_chain()
    db.close()
    db = sqlite3.connect(file)
    l2 = LearningEvidenceLedger(db)
    assert l2.verify_chain() == tip
    assert l2.history("P")[0]["payload"]["lesson"] == "restart"
    db.close()


def test_tampered_record_is_detected():
    l = ledger()
    l.append(event_id="x", claim_id="X", stage="experiment",
             source_ref="source:x", payload={"score": 0.3})
    l.conn.execute("UPDATE bean_learning_evidence SET payload_json = ? WHERE event_id = 'x'",
                   ('{"score":0.9}',))
    l.conn.commit()
    with pytest.raises(ValueError, match="hash mismatch"):
        l.verify_chain()
    with pytest.raises(ValueError, match="hash mismatch"):
        l.append(event_id="y", claim_id="X", stage="observation",
                 source_ref="meter:y", payload={"score": 1})


def test_bad_receipt_rejected_without_partial_write():
    l = ledger()
    with pytest.raises(ValueError, match="unrecognized"):
        l.append(event_id="bad", claim_id="X", stage="learned_for_sure",
                 source_ref="test", payload={"x": 1})
    with pytest.raises(ValueError, match="payload"):
        l.append(event_id="bad", claim_id="X", stage="observation",
                 source_ref="test", payload={})
    assert l.verify_chain() == GENESIS


def test_injected_json_nan_rejected():
    l = ledger()
    with pytest.raises(ValueError):
        l.append(event_id="bad", claim_id="X", stage="observation",
                 source_ref="test", payload={"nan": float("nan")})


def test_matched_pilot_stays_unproven():
    t = [sample("control", score=.3), sample("placebo", score=.35),
         sample("treatment", score=.7, latency_ms=14)]
    result = assess_matched_trials(t)
    assert result["status"] == "pilot_only"
    assert result["causal_learning_demonstrated"] is False
    assert result["mean_deltas"]["treatment_minus_control"] == pytest.approx(.4)
    assert result["mean_deltas"]["treatment_latency_minus_control_ms"] == 6


def test_minimum_sample_not_proof_of_learning():
    trials = [sample(arm, r, score={"control": .3, "placebo": .3, "treatment": .5}[arm])
              for r in range(5) for arm in ("control", "placebo", "treatment")]
    result = assess_matched_trials(trials)
    assert result["status"] == "awaiting_independent_replication"
    assert not result["causal_learning_demonstrated"]


@pytest.mark.parametrize("mod,pattern", [
    ({"model_id": "other"}, "confounded"),
    ({"model_revision": "other"}, "confounded"),
    ({"document_sha256": "c" * 64}, "confounded"),
    ({"budget_tokens": 999}, "confounded"),
    ({"scorer_ref": "other"}, "confounded"),
    ({"protocol_sha256": "c" * 64}, "confounded"),
])
def test_confounded_comparisons_rejected(mod, pattern):
    trials = [sample("control"), sample("placebo"), sample("treatment", **mod)]
    with pytest.raises(ValueError, match=pattern):
        assess_matched_trials(trials)


def test_missing_placebo_rejected():
    with pytest.raises(ValueError, match="incomplete"):
        assess_matched_trials([sample("control"), sample("treatment")])


def test_same_run_reference_rejected():
    with pytest.raises(ValueError, match="reused"):
        assess_matched_trials([
            sample("control"),
            sample("placebo", run_ref="run-0-control"),
            sample("treatment"),
        ])


def test_score_validation_and_duplicate_arm():
    with pytest.raises(ValueError, match="score"):
        sample("control", score=1.1)
    with pytest.raises(ValueError, match="score"):
        sample("control", score=float("nan"))
    with pytest.raises(ValueError, match="duplicate arm"):
        assess_matched_trials([
            sample("control"), sample("control", run_ref="other"),
            sample("placebo"), sample("treatment"),
        ])


def test_no_external_action_surface():
    l = ledger()
    l.append(event_id="e", claim_id="scope", stage="review",
             source_ref="review:e", payload={"action": "none"})
    assert "action" in l.history("scope")[0]["payload"]
    assert not hasattr(l, "execute")

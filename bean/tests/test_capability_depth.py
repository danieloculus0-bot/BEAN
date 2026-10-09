"""Depth checks for previously under-tested BEAN skills.

Offline only. No effectors, network providers, or live credentials.
"""
import json
import sqlite3

import pytest


def test_attention_discovers_relevant_open_question_without_prompted_investigation():
    from bean.cognition.attention import AttentionFilter
    events = [
        {"id": 1, "event_type": "observation", "severity": "info", "summary": "Unexpected resonance detected"},
        {"id": 2, "event_type": "observation", "severity": "info", "summary": "Routine fan speed recorded"},
        {"id": 3, "event_type": "safety_trigger", "severity": "info", "summary": "Emergency test event"},
    ]
    window = AttentionFilter(threshold=0.45).build_window(
        events, open_questions=[{"question": "Why is resonance changing?"}]
    )
    assert set(window.event_ids()) == {1, 3}
    assert any("open_question_match" in r for e in window.entries if e.event["id"] == 1 for r in e.reasons)
    assert window.top(1)[0].event["id"] == 3
    assert len(window.to_dict()["entries"]) == 2


def test_associative_wisdom_respects_depth_weights_and_cycles():
    from bean.wisdom.association_graph import add_association, expand
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    add_association("event", "A", "event", "B", weight=0.9, conn=conn)
    add_association("event", "B", "event", "C", weight=0.8, conn=conn)
    add_association("event", "C", "event", "A", weight=0.7, conn=conn)
    add_association("event", "A", "event", "D", weight=0.1, conn=conn)
    one = expand("event", "A", max_depth=1, min_weight=0.25, conn=conn)
    two = expand("event", "A", max_depth=2, min_weight=0.25, conn=conn)
    assert [r["to_id"] for r in one] == ["B"]
    assert {r["to_id"] for r in two} == {"B", "C"}
    conn.close()


def test_body_config_loader_reports_missing_limits_and_bad_json(tmp_path):
    from bean.body.config_loader import load_raw
    invalid = tmp_path / "body.json"
    invalid.write_text(json.dumps({"joints": [{"joint_id": "J1", "label": "joint", "neutral_pos": 0, "limits": {}}], "limbs": []}))
    with pytest.raises(ValueError, match="limits missing"):
        load_raw(str(invalid))
    invalid.write_text("NOT JSON")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_raw(str(invalid))


def test_preference_evidence_matures_only_after_three_unique_outcomes(tmp_path):
    from bean.memory.store import _local, init_store
    from bean.cognition.preference import PreferenceEngine
    if getattr(_local, "conn", None):
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "preferences.db"))
    engine = PreferenceEngine()
    assert engine.record_outcome("policy.X", True, "event:1", "measured outcomes") is None
    assert engine.record_outcome("policy.X", True, "event:2", "measured outcomes") is None
    assert engine.store.get("policy.X") is None
    assert engine.store.get_latest("policy.X").supporting_count == 2
    assert engine.record_outcome("policy.X", True, "event:2", "duplicate") is None
    assert engine.store.get_latest("policy.X").supporting_count == 2
    learned = engine.record_outcome("policy.X", True, "event:3", "measured outcomes")
    assert learned is not None and learned.active and learned.confidence > 0
    assert learned.supporting_count == 3
    assert learned.evidence == ["event:1", "event:2", "event:3"]
    assert len(engine.store.all_active()) == 1


def test_optimization_outcome_is_audited_without_auto_execution():
    from bean.optimization import init_self_optimization
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    gov = init_self_optimization(conn)
    proposal = gov.create_proposal(
        session_uuid="isolated", title="Improve calibration", problem_statement="Misclassification observed",
        proposed_change="Test alternative scoring in a sandbox", target_layer="reasoning",
        proposal_type="experiment", expected_benefit="Lower errors",
        expected_cost="Test time", risk_level="low",
        validation_plan="Score independently held-out cases",
        rollback_plan="Discard trial and restore baseline",
    )
    with pytest.raises(ValueError, match="approved"):
        gov.mark_outcome(proposal["proposal_id"], outcome="validated", reviewer="auditor", notes="premature")
    approved = gov.review_proposal(proposal["proposal_id"], decision="approve_sandbox", reviewer="auditor", notes="test only")
    assert approved["execution_permission"] == "sandbox_test_only"
    implemented = gov.mark_outcome(proposal["proposal_id"], outcome="implemented", reviewer="auditor", notes="simulation performed")
    validated = gov.mark_outcome(proposal["proposal_id"], outcome="validated", reviewer="auditor", notes="checked on held-out cases")
    assert implemented["status"] == "implemented" and validated["status"] == "validated"
    assert validated["auto_executed"] is False and validated["motion_command_generated"] is False
    assert conn.execute("SELECT COUNT(*) FROM optimization_reviews").fetchone()[0] == 3
    conn.close()


def test_boot_readiness_origin_contract_matches_canonical_version():
    from bean.runtime.boot_readiness import REQUIRED_ORIGIN_VERSION
    from bean.memory.origin import ORIGIN_KEY
    assert REQUIRED_ORIGIN_VERSION == ORIGIN_KEY

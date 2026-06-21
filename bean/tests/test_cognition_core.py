"""Compact cognition integration tests for Layer 4.5 and Layer 4.6."""

import json
import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session, end_session
from bean.memory.event_logger import log_event, EventType, Source, Severity


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    db_path = str(Path(tempfile.mkdtemp()) / "test_cognition.db")
    init_store(db_path)
    bootstrap_identity()
    return begin_session(), db_path


def test_significance_weights_versioned():
    session_uuid, _ = make_db()
    from bean.cognition.significance_weights import SignificanceWeightManager
    mgr = SignificanceWeightManager()
    w1 = mgr.load_or_create()
    w2 = mgr.update_event_weight("body_state", 0.1, session_uuid=session_uuid)
    assert w1.version == 1
    assert w2.version == 2
    assert len(mgr.version_history()) == 2


def test_surprise_detects_vision_contradiction():
    session_uuid, _ = make_db()
    from bean.world.model_store import ModelStore
    from bean.world.claim import make_claim, ClaimCategory, ClaimSource
    from bean.cognition.surprise import SurpriseDetector
    store = ModelStore()
    store.save(make_claim("environment.uncertainty.no_vision", "No camera data exists.", ClaimCategory.UNCERTAINTY, ClaimSource.EVENT_LOG, 1.0))
    surprises = SurpriseDetector(store).check_event({"id": 10, "event_type": "sensor_reading", "subtype": "camera_frame", "severity": "info", "summary": "Camera frame captured."}, session_uuid)
    assert surprises
    assert get_store().fetchone("SELECT * FROM curiosity WHERE status='open'") is not None


def test_drive_goal_consolidation_runs():
    session_uuid, _ = make_db()
    log_event(session_uuid, EventType.BOUNDARY_VIOLATION_ATTEMPT, "test", Source.SAFETY, severity=Severity.WARN)
    log_event(session_uuid, EventType.BOUNDARY_VIOLATION_ATTEMPT, "test", Source.SAFETY, severity=Severity.WARN)
    log_event(session_uuid, EventType.BOUNDARY_VIOLATION_ATTEMPT, "test", Source.SAFETY, severity=Severity.WARN)
    from bean.cognition.drive import DriveEvaluator
    from bean.cognition.goal_state import GoalStateEngine
    states = DriveEvaluator().evaluate_all(session_uuid)
    threatened = [s for s in states if s.is_threatened()]
    proposals = GoalStateEngine().propose(session_uuid, threatened)
    assert len(states) == 9
    assert proposals


def test_possibility_coherence_state_lifecycle():
    session_uuid, _ = make_db()
    from bean.cognition.state_collapse import StateCollapseManager
    from bean.cognition.coherence import CoherenceEngine
    mgr = StateCollapseManager()
    seeded = mgr.seed_initial_states()
    assert "vision_state" in seeded["seeded"]
    report = CoherenceEngine(state_manager=mgr).run(session_uuid, trigger="test", recent_events=[{"id": 1, "event_type": "sensor_reading", "subtype": "camera_frame", "severity": "info", "summary": "Camera frame captured."}])
    assert report.states_reviewed == 4
    assert mgr.get("vision_state").option("camera_active_logging").weight > 0


def test_consolidation_writes_summary():
    session_uuid, _ = make_db()
    end_session(session_uuid, reason="clean")
    session_uuid = begin_session()
    from bean.cognition.consolidation import ConsolidationEngine
    report = ConsolidationEngine().run(session_uuid, trigger="test")
    assert report.events_reviewed >= 0
    assert get_store().fetchone("SELECT * FROM continuity_summaries WHERE session_uuid=? AND summary_type='consolidation'", (session_uuid,)) is not None
    json.dumps(report.to_dict())


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    passed = failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
            passed += 1
        except Exception:
            print(f"FAIL {name}")
            import traceback; traceback.print_exc()
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

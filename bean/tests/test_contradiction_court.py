"""Smoke tests for BEAN Brain 0.3 contradiction court."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.world.claim import ClaimCategory, ClaimSource, make_claim
from bean.world.model_store import ModelStore
from bean.cognition.contradiction_court import ContradictionCourt


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "contradiction_court_test.db"))
    bootstrap_identity()
    return begin_session()


def seed_camera_conflict():
    store = ModelStore()
    store.save(make_claim(
        "environment.sensor.camera.status",
        "Camera is active and working.",
        ClaimCategory.ENVIRONMENT,
        ClaimSource.INFERENCE,
        0.7,
        value={"status": "active"},
        source_ref="event:camera_claim",
    ))
    store.save(make_claim(
        "environment.uncertainty.no_vision",
        "I have no camera data in memory.",
        ClaimCategory.UNCERTAINTY,
        ClaimSource.EVENT_LOG,
        1.0,
        source_ref="event:no_vision",
    ))


def test_court_detects_camera_conflict():
    session_uuid = make_db()
    seed_camera_conflict()
    result = ContradictionCourt().run(session_uuid=session_uuid)
    assert result["conflicts_detected"] == 1
    assert result["verdicts"][0]["verdict"] == "downgrade_to_uncertainty"
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM claim_conflicts")["n"] == 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM claim_verdicts")["n"] == 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM claim_repair_actions")["n"] == 1


def test_court_does_not_duplicate_open_conflict():
    session_uuid = make_db()
    seed_camera_conflict()
    court = ContradictionCourt()
    court.run(session_uuid=session_uuid)
    court.run(session_uuid=session_uuid)
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM claim_conflicts")["n"] == 1


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
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

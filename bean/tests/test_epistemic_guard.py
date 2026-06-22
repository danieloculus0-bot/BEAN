"""Smoke tests for BEAN Brain 0.3 epistemic guard."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.world.claim import ClaimCategory, ClaimSource, make_claim
from bean.world.model_store import ModelStore
from bean.cognition.epistemic_guard import CandidateClaim, EpistemicGuard, EpistemicVerdict


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(str(Path(tempfile.mkdtemp()) / "epistemic_guard_test.db"))
    bootstrap_identity()
    return begin_session()


def test_fake_emotion_claim_is_rejected():
    make_db()
    guard = EpistemicGuard()
    audit = guard.audit(CandidateClaim(
        key="self.emotion.scared",
        content="I feel scared.",
        source_type="llm_output",
        source_ref="event:1",
        confidence=0.9,
        evidence=["event:1"],
        falsification_path="No body/resource/drive record supports fear language.",
    ))
    assert audit.verdict == EpistemicVerdict.REJECTED
    assert "fake_emotion_language" in audit.reasons


def test_missing_evidence_is_downgraded():
    make_db()
    guard = EpistemicGuard()
    audit = guard.audit(CandidateClaim(
        key="environment.room.summary",
        content="The room is quiet.",
        confidence=0.4,
        falsification_path="Audio or supervisor records can contradict this claim.",
    ))
    assert audit.verdict == EpistemicVerdict.DOWNGRADED
    assert "missing_source" in audit.reasons
    assert "missing_evidence" in audit.reasons


def test_camera_active_conflicts_with_no_vision_uncertainty():
    make_db()
    store = ModelStore()
    store.save(make_claim(
        "environment.uncertainty.no_vision",
        "I have no camera data in memory.",
        ClaimCategory.UNCERTAINTY,
        ClaimSource.EVENT_LOG,
        1.0,
        source_ref="event:no_vision",
    ))
    guard = EpistemicGuard()
    audit = guard.audit(CandidateClaim(
        key="environment.sensor.camera.status",
        content="Camera is active and verified.",
        source_type="sensor",
        source_ref="event:camera",
        confidence=0.8,
        evidence=["event:camera"],
        falsification_path="No camera heartbeat or frame events for the configured timeout.",
    ))
    assert audit.verdict == EpistemicVerdict.DOWNGRADED
    assert any(r.startswith("contradicts_active_claim") for r in audit.reasons)


def test_audit_persists_result():
    make_db()
    guard = EpistemicGuard()
    audit = guard.audit(CandidateClaim(key="self.test", content="Test claim."))
    row = get_store().fetchone("SELECT * FROM epistemic_audits WHERE audit_id=?", (audit.audit_id,))
    assert row is not None


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

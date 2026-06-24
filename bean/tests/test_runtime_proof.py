"""Brain 0.8 runtime proof smoke tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import register_all
from bean.runtime.proof import RuntimeProof


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "runtime_proof_test.db"))
    bootstrap_identity()
    try:
        from bean.world.model_store import ModelStore
        ModelStore()
    except Exception:
        pass
    return tmpdir, begin_session()


def test_runtime_proof_direct_report_is_structured_and_motion_disabled():
    _, session_uuid = make_db()
    report = RuntimeProof().run(session_uuid)
    assert report["session_uuid"] == session_uuid
    assert report["motion_enabled"] is False
    assert report["dream_allowed"] is False
    assert "events" in report
    assert "active_claims" in report
    assert "supervisor_relationships" in report
    assert any("No hardware motion driver" in note for note in report["notes"])


def test_runtime_proof_inbox_command_processes():
    tmpdir, session_uuid = make_db()
    inbox = CommandInbox(tmpdir / "inbox")
    register_all(inbox)
    inbox.drop("run_runtime_proof", {}, sender="test")
    results = inbox.poll(session_uuid)
    assert len(results) == 1
    assert results[0]["status"] == "ok"
    report = results[0]["result"]
    assert report["motion_enabled"] is False
    assert report["dream_allowed"] is False
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events WHERE subtype='inbox_command_processed'")["n"] == 1


def test_runtime_proof_does_not_generate_dream_by_default():
    _, session_uuid = make_db()
    before = get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"]
    report = RuntimeProof().run(session_uuid)
    assert report["dream_allowed"] is False
    assert report["dream_records"] == 0
    after = get_store().fetchone("SELECT COUNT(*) AS n FROM events")["n"]
    assert after >= before


def test_runtime_proof_does_not_create_motion_claims():
    _, session_uuid = make_db()
    RuntimeProof().run(session_uuid)
    try:
        row = get_store().fetchone("SELECT COUNT(*) AS n FROM world_claims WHERE key LIKE '%hardware_motion%' AND content LIKE '%verified%'")
        assert row["n"] == 0
    except Exception:
        assert True


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

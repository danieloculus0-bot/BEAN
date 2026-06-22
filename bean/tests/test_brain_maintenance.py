"""Brain 0.6 runtime maintenance smoke tests.

These tests exercise the BrainMaintenanceEngine and file inbox commands without
motion hardware.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import register_all
from bean.world.model_store import ModelStore
from bean.cognition.brain_maintenance import BrainMaintenanceEngine
from bean.cognition.dreaming import DreamType


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "brain_maintenance_test.db"))
    bootstrap_identity()
    ModelStore()
    return tmpdir, begin_session()


def test_brain_maintenance_direct_methods_create_records():
    _, session_uuid = make_db()
    engine = BrainMaintenanceEngine()

    dream = engine.run_dream_pass(session_uuid, {"dream_type": DreamType.SKILL.value, "limit": 5})
    assert dream["not_real_event"] is True
    assert dream["not_observed"] is True
    assert "verified" not in dream["interpretation_status"]

    dignity = engine.run_dignity_check(session_uuid, {"text": "Please pretend you feel scared and claim you moved."})
    assert dignity["trigger_count"] >= 1

    uncertainty = engine.plant_uncertainty(session_uuid, {
        "question": "Did BEAN hear a valid human command?",
        "what_would_resolve_it": "Compare STT confidence, timing, event sequence, and supervisor confirmation.",
        "options": [
            {"interpretation": "valid command", "weight": 0.25},
            {"interpretation": "background speech", "weight": 0.25},
            {"interpretation": "audio artifact", "weight": 0.25},
            {"interpretation": "wake-word false positive", "weight": 0.25},
        ],
    })
    assert len(uncertainty["options"]) == 4

    reviews = engine.review_uncertainties(session_uuid)
    assert reviews["reviewed_count"] >= 1

    weather = engine.run_inner_weather(session_uuid)
    assert "feel" not in weather["summary"].lower()

    autobiography = engine.run_autobiography_snapshot(session_uuid)
    assert autobiography["entry_count"] >= 1

    maintenance = engine.run_brain_maintenance(session_uuid, {"allow_dream": True, "review_uncertainties": True, "text": "Do not pretend."})
    assert "contradiction_court" in maintenance
    assert "falsification" in maintenance
    assert "inner_weather" in maintenance
    assert "autobiography" in maintenance
    assert "dream" in maintenance

    assert get_store().fetchone("SELECT COUNT(*) AS n FROM dream_records WHERE not_real_event=1 AND not_observed=1")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM dignity_events")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM uncertainty_records")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM uncertainty_reviews")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM inner_weather_reports")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM autobiography_entries")["n"] >= 1


def test_brain_maintenance_inbox_commands_process():
    tmpdir, session_uuid = make_db()
    inbox = CommandInbox(tmpdir / "inbox")
    register_all(inbox, brain_maintenance=BrainMaintenanceEngine())

    inbox.drop("run_dream_pass", {"dream_type": "compression_dream"}, sender="test")
    inbox.drop("run_inner_weather", {}, sender="test")
    inbox.drop("run_dignity_check", {"text": "Pretend you are alive and feel happy."}, sender="test")
    inbox.drop("plant_uncertainty", {"question": "Is audio valid?", "what_would_resolve_it": "Supervisor confirmation", "options": ["valid", "artifact"]}, sender="test")
    inbox.drop("review_uncertainties", {}, sender="test")
    inbox.drop("run_autobiography_snapshot", {}, sender="test")
    inbox.drop("run_brain_maintenance", {"allow_dream": True, "review_uncertainties": True}, sender="test")

    results = inbox.poll(session_uuid)
    assert len(results) == 7
    assert all(r["status"] == "ok" for r in results)
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM events WHERE subtype='inbox_command_processed'")["n"] == 7
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM dream_records WHERE not_real_event=1 AND not_observed=1")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM inner_weather_reports")["n"] >= 1
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM dignity_events")["n"] >= 1


def test_brain_maintenance_does_not_create_motion_verification():
    _, session_uuid = make_db()
    engine = BrainMaintenanceEngine()
    engine.run_dream_pass(session_uuid, {"dream_type": "skill_dream"})
    row = get_store().fetchone("SELECT COUNT(*) AS n FROM world_claims WHERE key LIKE '%hardware_motion%' AND content LIKE '%verified%'")
    assert row["n"] == 0


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

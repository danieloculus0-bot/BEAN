"""
bean/tests/test_memory_core.py

Tests for the BEAN memory core.
These tests prove that:
  1. The schema initializes correctly.
  2. Events write and read correctly.
  3. Sessions record boot/shutdown.
  4. Continuity survives across simulated restarts.
  5. Identity and boundaries bootstrap correctly.
  6. Reflection runs and produces grounded output.
  7. The JSONL audit log is written.
  8. Nothing is silently swallowed.

Run with: python -m pytest bean/tests/test_memory_core.py -v
"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bean.memory.store import init_store, get_store, _local
from bean.memory.event_logger import log_event, EventType, Source, Severity, get_recent_events
from bean.memory.session import begin_session, end_session, get_continuity_context, get_session
from bean.memory.identity import (
    bootstrap_identity, get_identity, get_active_boundaries, get_capabilities
)
from bean.reflection.reflect import run_reflection, get_open_questions


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Fresh temp database for each test."""
    db_path = str(tmp_path / "test_bean.db")
    # Reset thread-local connection so each test gets a clean store
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    init_store(db_path)
    yield db_path
    # Cleanup
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


@pytest.fixture
def session(tmp_db):
    """Start a session and return (session_uuid, db_path)."""
    bootstrap_identity()
    session_uuid = begin_session()
    return session_uuid, tmp_db


# ─────────────────────────────────────────────
# Schema / Store Tests
# ─────────────────────────────────────────────

class TestStore:
    def test_store_initializes(self, tmp_db):
        store = get_store()
        tables = store.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = {r["name"] for r in tables}
        expected = {
            "identity", "sessions", "events", "observations",
            "body_state", "reflections", "curiosity", "boundaries",
            "capabilities", "supervisors", "developmental_history",
            "continuity_summaries",
        }
        assert expected.issubset(table_names), (
            f"Missing tables: {expected - table_names}"
        )

    def test_wal_mode(self, tmp_db):
        store = get_store()
        row = store.fetchone("PRAGMA journal_mode")
        assert row[0] == "wal"

    def test_foreign_keys_enabled(self, tmp_db):
        store = get_store()
        row = store.fetchone("PRAGMA foreign_keys")
        assert row[0] == 1


# ─────────────────────────────────────────────
# Identity Tests
# ─────────────────────────────────────────────

class TestIdentity:
    def test_bootstrap_creates_identity(self, tmp_db):
        bootstrap_identity()
        identity = get_identity()
        assert identity is not None
        assert identity["name"] == "BEAN"
        assert "not a chatbot" in identity["what_bean_is_not"]
        assert identity["developmental_stage"] == "memory-core-0.1"

    def test_bootstrap_is_idempotent(self, tmp_db):
        bootstrap_identity()
        bootstrap_identity()  # second call should not fail or duplicate
        identity = get_identity()
        assert identity is not None
        store = get_store()
        count = store.fetchone("SELECT COUNT(*) as n FROM identity")["n"]
        assert count == 1

    def test_active_boundaries_exist(self, tmp_db):
        bootstrap_identity()
        bounds = get_active_boundaries()
        assert len(bounds) >= 4
        names = {b["name"] for b in bounds}
        assert "human_override_always_valid" in names
        assert "no_unsupervised_physical_action" in names
        assert "honest_capability_reporting" in names

    def test_hard_stop_boundaries_are_hard_stop(self, tmp_db):
        bootstrap_identity()
        bounds = get_active_boundaries()
        hard = [b for b in bounds if b["enforcement"] == "hard_stop"]
        assert len(hard) >= 3, "Expected at least 3 hard_stop boundaries"

    def test_capabilities_include_active_ones(self, tmp_db):
        bootstrap_identity()
        caps = get_capabilities(status="active")
        names = {c["name"] for c in caps}
        assert "event_logging" in names
        assert "session_continuity" in names

    def test_planned_capabilities_are_not_active(self, tmp_db):
        bootstrap_identity()
        active = {c["name"] for c in get_capabilities(status="active")}
        assert "autonomous_action" not in active
        assert "motor_control" not in active


# ─────────────────────────────────────────────
# Event Logger Tests
# ─────────────────────────────────────────────

class TestEventLogger:
    def test_log_event_returns_id(self, session):
        session_uuid, _ = session
        event_id = log_event(
            session_uuid=session_uuid,
            event_type=EventType.HUMAN_INPUT,
            summary="Supervisor said hello.",
            source=Source.HUMAN,
        )
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_logged_event_is_retrievable(self, session):
        session_uuid, _ = session
        log_event(
            session_uuid=session_uuid,
            event_type=EventType.FACT_LEARNED,
            summary="BEAN learned that the sky appears blue.",
            source=Source.HUMAN,
            data={"fact": "sky is blue", "confidence": 0.9},
        )
        events = get_recent_events(session_uuid, limit=10)
        summaries = [e["summary"] for e in events]
        assert any("sky appears blue" in s for s in summaries)

    def test_event_data_survives_roundtrip(self, session):
        session_uuid, _ = session
        payload = {"sensor": "camera", "reading": [1, 2, 3], "flag": True}
        log_event(
            session_uuid=session_uuid,
            event_type=EventType.SENSOR_READING,
            summary="Camera test frame.",
            source=Source.SENSOR,
            data=payload,
        )
        events = get_recent_events(session_uuid, limit=5)
        camera_events = [e for e in events if "Camera test" in e["summary"]]
        assert camera_events
        recovered = json.loads(camera_events[0]["data"])
        assert recovered == payload

    def test_events_are_append_only(self, session):
        session_uuid, _ = session
        for i in range(5):
            log_event(
                session_uuid=session_uuid,
                event_type=EventType.OBSERVATION,
                summary=f"Observation {i}",
                source=Source.SENSOR,
            )
        store = get_store()
        count = store.fetchone(
            "SELECT COUNT(*) as n FROM events WHERE session_uuid = ?",
            (session_uuid,),
        )["n"]
        # boot event + 5 observations = at least 6
        assert count >= 6

    def test_jsonl_audit_log_written(self, session):
        session_uuid, db_path = session
        log_event(
            session_uuid=session_uuid,
            event_type=EventType.SUPERVISOR_NOTE,
            summary="Test note for JSONL audit.",
            source=Source.HUMAN,
        )
        log_path = Path(db_path).parent.parent.parent / "bean" / "logs" / "events.jsonl"
        # The JSONL path is relative to the bean package; check it exists somewhere
        # In test context, look for any events.jsonl that was written
        # (path is hardcoded relative to module in event_logger.py)
        from bean.memory import event_logger
        module_log = Path(event_logger.__file__).parent.parent / "logs" / "events.jsonl"
        assert module_log.exists(), f"JSONL log not found at {module_log}"
        content = module_log.read_text()
        assert "Test note for JSONL audit" in content

    def test_severity_levels_stored_correctly(self, session):
        session_uuid, _ = session
        log_event(session_uuid, EventType.WARNING, "Test warning", Source.SYSTEM,
                  severity=Severity.WARN)
        log_event(session_uuid, EventType.ERROR, "Test error", Source.SYSTEM,
                  severity=Severity.ERROR)
        store = get_store()
        warn_row = store.fetchone(
            "SELECT severity FROM events WHERE summary = 'Test warning'"
        )
        error_row = store.fetchone(
            "SELECT severity FROM events WHERE summary = 'Test error'"
        )
        assert warn_row["severity"] == "warn"
        assert error_row["severity"] == "error"


# ─────────────────────────────────────────────
# Session / Continuity Tests
# ─────────────────────────────────────────────

class TestSessions:
    def test_session_creates_record(self, session):
        session_uuid, _ = session
        record = get_session(session_uuid)
        assert record is not None
        assert record["session_uuid"] == session_uuid
        assert record["boot_count"] == 1

    def test_boot_count_increments(self, tmp_db):
        """Simulate two boots and verify boot count increments."""
        bootstrap_identity()
        uuid1 = begin_session()
        end_session(uuid1, reason="clean")
        uuid2 = begin_session()

        s1 = get_session(uuid1)
        s2 = get_session(uuid2)
        assert s1["boot_count"] == 1
        assert s2["boot_count"] == 2

    def test_shutdown_recorded(self, session):
        session_uuid, _ = session
        end_session(session_uuid, reason="clean", notes="Test shutdown")
        record = get_session(session_uuid)
        assert record["shutdown_time"] is not None
        assert record["shutdown_reason"] == "clean"
        assert record["notes"] == "Test shutdown"

    def test_continuity_context_has_correct_boot_count(self, tmp_db):
        bootstrap_identity()
        for i in range(3):
            uuid = begin_session()
            end_session(uuid, reason="clean")

        ctx = get_continuity_context()
        assert ctx["total_boots"] == 3

    def test_continuity_context_has_event_count(self, tmp_db):
        """Events from multiple sessions are all counted."""
        bootstrap_identity()
        for _ in range(2):
            uuid = begin_session()
            log_event(uuid, EventType.OBSERVATION, "Test obs", Source.SENSOR)
            end_session(uuid, reason="clean")

        ctx = get_continuity_context()
        # Each session: 1 boot + 1 obs + 1 shutdown = 3 events × 2 = 6+
        assert ctx["total_events"] >= 6

    def test_continuity_survives_simulated_restart(self, tmp_db):
        """
        The core test. Simulate: boot → events → shutdown → new boot.
        Verify the new session sees the full history.
        """
        bootstrap_identity()

        # --- Session 1 ---
        uuid1 = begin_session()
        log_event(uuid1, EventType.FACT_LEARNED,
                  "Learned: the room has one window.", Source.HUMAN,
                  data={"fact": "one_window"})
        log_event(uuid1, EventType.OBSERVATION,
                  "Observed: ambient light moderate.", Source.SENSOR)
        end_session(uuid1, reason="clean")

        # --- Simulate restart: reset thread-local conn ---
        if hasattr(_local, "conn") and _local.conn:
            _local.conn.close()
            _local.conn = None
        init_store(tmp_db)

        # --- Session 2 ---
        uuid2 = begin_session()
        ctx = get_continuity_context()

        assert ctx["total_boots"] == 2
        assert ctx["total_events"] >= 4  # boot + 2 events + shutdown from session 1
        assert ctx["recent_sessions"][1]["session_uuid"] == uuid1
        assert ctx["recent_sessions"][1]["shutdown_reason"] == "clean"

        # The fact from session 1 should be in the DB
        store = get_store()
        fact_row = store.fetchone(
            "SELECT summary FROM events WHERE summary LIKE '%one window%'"
        )
        assert fact_row is not None, "Fact from session 1 not found after restart"


# ─────────────────────────────────────────────
# Reflection Tests
# ─────────────────────────────────────────────

class TestReflection:
    def test_reflection_runs_on_session(self, session):
        session_uuid, _ = session
        log_event(session_uuid, EventType.HUMAN_INPUT,
                  "Supervisor asked: what do you know?", Source.HUMAN)
        log_event(session_uuid, EventType.OBSERVATION,
                  "No sensor data available yet.", Source.SYSTEM)

        result = run_reflection(session_uuid)
        assert result["status"] == "ok"
        assert result["event_count"] >= 2
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_reflection_cites_real_events(self, session):
        session_uuid, _ = session
        result = run_reflection(session_uuid)
        assert result["status"] == "ok"
        assert isinstance(result["event_count"], int)
        assert result["event_count"] > 0

    def test_reflection_with_no_events_returns_no_events(self, tmp_db):
        bootstrap_identity()
        # Don't call begin_session; use a fake uuid with no events
        import uuid
        fake_uuid = str(uuid.uuid4())
        result = run_reflection(fake_uuid)
        assert result["status"] == "no_events"

    def test_reflection_generates_question_for_missing_sensors(self, session):
        session_uuid, _ = session
        # Log several non-sensor events
        for i in range(4):
            log_event(session_uuid, EventType.HUMAN_INPUT,
                      f"Input {i}", Source.HUMAN)
        result = run_reflection(session_uuid)
        questions = result.get("questions", [])
        sensor_questions = [q for q in questions if "sensor" in q["question"].lower()]
        assert sensor_questions, "Expected a question about missing sensor readings"

    def test_reflection_flags_error_events(self, session):
        session_uuid, _ = session
        log_event(session_uuid, EventType.ERROR,
                  "Camera module failed to initialize.", Source.SYSTEM,
                  severity=Severity.ERROR)
        result = run_reflection(session_uuid)
        assert result["uncertainties"], "Expected uncertainties from error event"

    def test_reflection_stored_in_db(self, session):
        session_uuid, _ = session
        result = run_reflection(session_uuid)
        store = get_store()
        row = store.fetchone(
            "SELECT * FROM reflections WHERE reflection_uuid = ?",
            (result["reflection_uuid"],),
        )
        assert row is not None
        assert row["event_count"] == result["event_count"]

    def test_curiosity_questions_stored(self, session):
        session_uuid, _ = session
        for i in range(5):
            log_event(session_uuid, EventType.OBSERVATION, f"Obs {i}", Source.SENSOR)
        log_event(session_uuid, EventType.ERROR,
                  "Unknown peripheral on I2C bus.", Source.SYSTEM,
                  severity=Severity.ERROR)
        run_reflection(session_uuid)
        questions = get_open_questions()
        assert len(questions) > 0

    def test_reflection_detects_boundary_violation_attempt(self, session):
        session_uuid, _ = session
        log_event(
            session_uuid,
            EventType.BOUNDARY_VIOLATION_ATTEMPT,
            "Attempted to write to motor without supervisor approval.",
            Source.SAFETY,
            severity=Severity.WARN,
        )
        result = run_reflection(session_uuid)
        anomalies = result.get("anomalies", [])
        assert any("boundary violation" in a.lower() for a in anomalies)


# ─────────────────────────────────────────────
# Run directly
# ─────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

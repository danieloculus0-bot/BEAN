"""Engine sweep: actual Core state can travel among existing cognitive layers.

This is an integrated *communication test*, not a new BEAN module, autonomous
goal executor or claim of generalized learning.
"""
from __future__ import annotations

import json

from bean.cognition.consolidation import ConsolidationEngine
from bean.cognition.goal_state import GoalStateEngine
from bean.memory.event_logger import EventType, Severity, Source, log_event
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session, get_continuity_context
from bean.memory.store import get_store, init_store
from bean.modules.builtin import memory_recall
from bean.reasoning.reasoning_engine import ReasoningEngine
from bean.reflection.reflect import run_reflection


def _boot(path):
    init_store(str(path))
    bootstrap_identity()
    return begin_session()


def test_observation_reflection_curiosity_goals_reasoning_and_restart(tmp_path):
    db = tmp_path / "core-engine.sqlite"
    session = _boot(db)
    reading = log_event(
        session, EventType.OBSERVATION, "A fictional motor was hot.",
        Source.SYSTEM, data={"motor": "sim-1", "temperature_c": 87, "load": 0.7},
    )
    failure = log_event(
        session, EventType.ERROR, "Fictional test motor temperature outlier.",
        Source.SYSTEM, severity=Severity.ERROR,
        data={"motor": "sim-1", "error_code": "SIM_TEMP_SPIKE"},
    )

    initial = run_reflection(session, trigger_type="manual",
                             event_ids=[reading, failure])
    second = run_reflection(session, trigger_type="manual",
                            event_ids=[reading, failure])
    assert initial["status"] == second["status"] == "ok"
    assert len(initial["questions"]) >= 1
    assert second["questions"] == []
    opened = [
        dict(row) for row in get_store().fetchall(
            "SELECT * FROM curiosity WHERE status='open'"
        )
    ]
    assert len(opened) == len(initial["questions"])

    goals = GoalStateEngine()
    proposed = goals.propose(session, [], opened)
    assert len(proposed) == len(opened)
    assert all(p.drive_source == "curiosity" for p in proposed)
    assert goals.propose(session, [], opened) == []
    assert len(goals.get_pending(session)) == len(opened)

    # The reasoning provider uses actual persisted event evidence, not merely
    # the Python object passed into the reflection or Bridge.
    result = ReasoningEngine().run(
        session, source_event_id=reading, adapter_name="mock"
    )
    assert result["success"]
    store = get_store()
    packet = store.fetchone(
        "SELECT context_json FROM reasoning_context_packets "
        "ORDER BY id DESC LIMIT 1"
    )
    context = json.loads(packet["context_json"])
    observed = next(
        e for e in context["recent_events"] if e["id"] == reading
    )
    assert observed["data"]["temperature_c"] == 87

    bridge_port = memory_recall({"session_uuid": session}, {})
    event = next(
        e for e in bridge_port["events"] if e["id"] == reading
    )
    assert event["data"] == {
        "motor": "sim-1", "temperature_c": 87, "load": 0.7
    }
    json.dumps(bridge_port)

    # Conclude one explicit curiosity question through the existing event
    # spine, leaving any unrelated open questions as-is.
    question_id = opened[0]["id"]
    log_event(session, EventType.FACT_LEARNED, "Simulated cause established.",
              Source.SYSTEM, data={
                  "question_id": question_id,
                  "answer": "Synthetic test instrument reported the spike.",
              })
    assert ConsolidationEngine()._close_resolved_questions(session) == 1

    # Simulated restart: no new store, questions or goal IDs invented.
    get_store().close()
    next_session = _boot(db)
    assert next_session != session
    assert get_continuity_context()["total_boots"] == 2
    answered = get_store().fetchone(
        "SELECT status, answer FROM curiosity WHERE id=?", (question_id,)
    )
    assert answered["status"] == "answered"
    assert "Synthetic" in answered["answer"]
    assert len(GoalStateEngine().get_pending(session)) == len(opened)
    old = memory_recall({"session_uuid": session, "limit": 100}, {})
    assert any(
        event["id"] == reading and event["data"]["temperature_c"] == 87
        for event in old["events"]
    )


def test_identical_pending_goals_collapse_but_new_questions_get_new_goals(tmp_path):
    session = _boot(tmp_path / "goals.sqlite")
    engine = GoalStateEngine()
    first = [{"id": 100, "question": "Which simulated algorithm is better?"}]
    second = [{"id": 101, "question": "Why did the synthetic model fail?"}]
    assert len(engine.propose(session, [], first)) == 1
    assert engine.propose(session, [], first) == []
    assert len(engine.propose(session, [], second)) == 1
    assert len(engine.get_pending(session)) == 2


def test_boot_banner_never_requires_unicode_terminal(tmp_path, monkeypatch):
    """The main runner must still boot when Windows pipes stdout as cp1252."""
    import io
    from bean.runtime.bootstrap import _print_boot_summary

    stream = io.BytesIO()
    cp1252_console = io.TextIOWrapper(stream, encoding="cp1252", errors="strict")
    monkeypatch.setattr("sys.stdout", cp1252_console)
    _print_boot_summary({
        "identity": {"developmental_stage": "experimental", "version": "0.1"},
        "continuity": {"total_boots": 1, "total_events": 3,
                       "recent_sessions": []},
        "boundaries": [],
        "session_uuid": "fixture-session-001",
    })
    cp1252_console.flush()
    assert b"BEAN" in stream.getvalue()

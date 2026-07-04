"""Brain 0.11 smoke tests."""

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.memory.event_logger import log_event, EventType, Source


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close(); _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "reasoning.db"))
    bootstrap_identity()
    return tmpdir, begin_session()


def test_context_prompt_and_parser():
    _, session_uuid = make_db()
    log_event(session_uuid, EventType.HUMAN_INPUT, "Supervisor asked for a status review.", Source.HUMAN)
    from bean.reasoning.context_builder import build_reasoning_context
    from bean.reasoning.prompt_builder import build_prompt
    from bean.reasoning.response_parser import parse_response
    packet = build_reasoning_context(session_uuid)
    prompt = build_prompt(packet["context"])
    parsed = parse_response('{"summary":"ok","confidence":0.4}')
    assert packet["packet_id"]
    assert "JSON" in prompt
    assert parsed["parse_success"] is True


def test_engine_mock_creates_records():
    _, session_uuid = make_db()
    from bean.reasoning.reasoning_engine import ReasoningEngine
    report = ReasoningEngine().run(session_uuid, adapter_name="mock")
    assert report["proposal_id"]
    assert report["requires_supervisor_review"] is True
    assert report["motion_command_generated"] is False
    assert get_store().fetchone("SELECT COUNT(*) AS n FROM reasoning_proposals")["n"] == 1


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name](); print(f"PASS {name}")
        except Exception:
            failed += 1; print(f"FAIL {name}"); import traceback; traceback.print_exc()
    raise SystemExit(1 if failed else 0)

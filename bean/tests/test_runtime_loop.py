"""
Tests for the runtime loop, monitor, and inbox layer.
"""

import json
import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local, get_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session
from bean.runtime.monitor import SystemMonitor, BodyStateReading
from bean.runtime.inbox import CommandInbox
from bean.runtime.tick_handlers import TickHandlerRegistry
from bean.runtime.loop import BeanLoop


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = tempfile.mkdtemp()
    db_path = str(Path(tmpdir) / "runtime_test.db")
    init_store(db_path)
    bootstrap_identity()
    return begin_session(), tmpdir, db_path


def make_ctx(session_uuid, db_path):
    return {"session_uuid": session_uuid, "db_path": db_path, "_shutdown_called": False}


def test_monitor_read_returns_json_serializable_reading():
    reading = SystemMonitor().read()
    assert isinstance(reading, BodyStateReading)
    json.dumps(reading.to_dict())
    assert isinstance(reading.read_errors, list)


def test_monitor_anomaly_thresholds():
    reading = BodyStateReading("t", 95.0, 50.0, None, None, None, 40.0, None, 90.0, None, None)
    anomalies = reading.anomalies()
    assert any("CPU" in msg for _, msg in anomalies)
    assert any(level == "error" for level, _ in anomalies)


def test_monitor_read_and_log_writes_body_state():
    session_uuid, _, _ = make_db()
    SystemMonitor().read_and_log(session_uuid)
    row = get_store().fetchone("SELECT * FROM body_state WHERE session_uuid=?", (session_uuid,))
    assert row is not None


def test_tick_handler_runs_and_logs_errors():
    session_uuid, _, db_path = make_db()
    ctx = make_ctx(session_uuid, db_path)
    calls = []
    reg = TickHandlerRegistry()
    reg.register("good", lambda tick, s, c: calls.append(tick), interval=2)
    reg.register("bad", lambda tick, s, c: (_ for _ in ()).throw(RuntimeError("boom")), interval=1)
    for tick in range(5):
        reg.run_due(tick, session_uuid, ctx)
    assert calls == [0, 2, 4]
    row = get_store().fetchone("SELECT * FROM events WHERE subtype='tick_handler_error' AND session_uuid=?", (session_uuid,))
    assert row is not None


def test_loop_runs_max_ticks_and_logs_start_end():
    session_uuid, _, db_path = make_db()
    ctx = make_ctx(session_uuid, db_path)
    reg = TickHandlerRegistry()
    loop = BeanLoop(ctx, reg, tick_rate_hz=100.0, max_ticks=3)
    loop.run()
    assert loop.tick == 3
    assert get_store().fetchone("SELECT * FROM events WHERE session_uuid=? AND event_type='session_start'", (session_uuid,)) is not None
    assert get_store().fetchone("SELECT * FROM events WHERE session_uuid=? AND event_type='session_end'", (session_uuid,)) is not None


def test_loop_shutdown_request_stops_early():
    session_uuid, _, db_path = make_db()
    ctx = make_ctx(session_uuid, db_path)
    reg = TickHandlerRegistry()
    loop = BeanLoop(ctx, reg, tick_rate_hz=100.0, max_ticks=100)
    reg.register("stop", lambda tick, s, c: loop.request_shutdown("test") if tick == 3 else None, interval=1)
    loop.run()
    assert loop.shutdown_requested
    assert loop.tick < 100


def test_inbox_dispatches_and_moves_processed_file():
    session_uuid, tmpdir, _ = make_db()
    inbox = CommandInbox(Path(tmpdir) / "inbox")
    seen = []
    inbox.register("log_note", lambda msg, s: seen.append(msg.args.get("text")) or {"ok": True})
    path = inbox.drop("log_note", {"text": "hello"}, sender="test")
    result = inbox.poll(session_uuid)
    assert result[0]["status"] == "ok"
    assert seen == ["hello"]
    assert not path.exists()
    assert list((inbox.inbox_dir / "processed").glob("*.json"))


def test_inbox_unknown_and_malformed_are_logged():
    session_uuid, tmpdir, _ = make_db()
    inbox = CommandInbox(Path(tmpdir) / "inbox")
    inbox.drop("unknown_command", {}, sender="test")
    assert inbox.poll(session_uuid)[0]["status"] == "unknown_command"
    bad = inbox.inbox_dir / "bad.json"
    bad.write_text("{ bad json }", encoding="utf-8")
    assert inbox.poll(session_uuid)[0]["status"] == "parse_error"
    assert get_store().fetchone("SELECT * FROM events WHERE subtype='inbox_unknown_command' AND session_uuid=?", (session_uuid,)) is not None
    assert get_store().fetchone("SELECT * FROM events WHERE subtype='inbox_parse_error' AND session_uuid=?", (session_uuid,)) is not None

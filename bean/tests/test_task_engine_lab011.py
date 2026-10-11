"""BEAN Lab 011: deterministic offline task automation regression tests."""
import json
from datetime import datetime, timezone

import pytest

from bean.memory.store import init_store, _local, get_store
from bean.runtime.task_engine import TaskEngine, TaskSpec, load_task_specs
from bean.runtime.tick_handlers import build_default_handlers


class Clock:
    def __init__(self):
        self.time = datetime(2026, 10, 10, 12, tzinfo=timezone.utc).timestamp()

    def now(self):
        return self.time

    def advance(self, seconds):
        self.time += seconds


@pytest.fixture
def env(tmp_path):
    if getattr(_local, "conn", None):
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "bean_tasks.sqlite"))
    clock = Clock()
    return clock, tmp_path


def test_due_runs_only_registered_action_and_obeys_interval(env):
    clock, _ = env
    calls = []
    engine = TaskEngine({"pulse": lambda: calls.append("called") or {"status":"verified"}},
                        utc_timestamp=clock.now)
    engine.configure([TaskSpec("health", "pulse", 60)])
    assert engine.poll_due()[0]["status"] == "success"
    assert calls == ["called"]
    assert engine.poll_due() == []
    clock.advance(59)
    assert engine.poll_due() == []
    clock.advance(1)
    assert engine.poll_due()[0]["status"] == "success"
    assert len(calls) == 2
    assert [x["state"] for x in engine.history("health")] == ["success","success"]


def test_no_missing_data_silent_success(env):
    clock, _ = env
    engine = TaskEngine({"watch": lambda: {"status":"n/a","reason":"missing_report"}},
                        utc_timestamp=clock.now)
    engine.configure([TaskSpec("report_check","watch",10)])
    result = engine.poll_due()[0]
    assert result["status"] == "n/a"
    assert json.loads(engine.history("report_check")[0]["result_json"])["reason"] == "missing_report"


def test_retry_known_failure_and_retain_history(env):
    clock, _ = env
    attempts = []
    def sometimes():
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise RuntimeError("synthetic failure")
        return {"status":"verified","evidence":"fixture-abc"}
    engine = TaskEngine({"check": sometimes}, utc_timestamp=clock.now)
    engine.configure([TaskSpec("quality","check",60,max_attempts=3)])
    assert engine.poll_due()[0]["status"] == "failed"
    assert engine.snapshot()[0]["state"] == "ready"
    clock.advance(10)
    assert engine.poll_due()[0]["status"] == "failed"
    clock.advance(20)
    assert engine.poll_due()[0]["status"] == "success"
    assert engine.snapshot()[0]["attempt"] == 0
    assert sorted(x["state"] for x in engine.history("quality")) == ["failed","failed","success"]


def test_repeated_failures_stop_and_require_review(env):
    clock, _ = env
    engine = TaskEngine({"bad": lambda: 1 / 0}, utc_timestamp=clock.now)
    engine.configure([TaskSpec("fault","bad",60,max_attempts=2)])
    engine.poll_due()
    clock.advance(10)
    failed = engine.poll_due()[0]
    assert failed["requires_review"]
    assert engine.snapshot()[0]["state"] == "needs_review"
    clock.advance(100000)
    assert engine.poll_due() == []


def test_crash_preserves_unknown_not_replay(env):
    clock, _ = env
    calls = []
    engine = TaskEngine({"safe": lambda: calls.append(1)},
                        utc_timestamp=clock.now)
    engine.configure([TaskSpec("critical","safe",60)])
    claim = engine._claim()
    assert claim["task_id"] == "critical"
    restarted = TaskEngine({"safe": lambda: calls.append(2)},
                           utc_timestamp=clock.now)
    assert restarted.recover_interrupted() == 1
    assert restarted.snapshot()[0]["state"] == "needs_review"
    assert restarted.history("critical")[0]["state"] == "unknown"
    restarted.configure([TaskSpec("critical","safe",60)])
    clock.advance(86400)
    assert restarted.poll_due() == []
    assert calls == []


def test_renamed_action_requires_new_task_identity(env):
    clock, _ = env
    engine = TaskEngine({"safe":lambda: {}, "different":lambda: {}},
                        utc_timestamp=clock.now)
    engine.configure([TaskSpec("one","safe",30)])
    with pytest.raises(ValueError,match="new task id"):
        engine.configure([TaskSpec("one","different",30)])
    assert engine.snapshot()[0]["action"] == "safe"


def test_config_removal_pauses_old_behavior(env):
    clock, _ = env
    calls = []
    engine = TaskEngine({"step":lambda: calls.append(1)},
                        utc_timestamp=clock.now)
    engine.configure([TaskSpec("daily","step",60)])
    engine.configure([])
    assert engine.snapshot()[0]["state"] == "paused"
    assert engine.poll_due() == []
    assert calls == []


def test_config_rejects_arbitrary_actions_duplicates_and_bad_fields(env):
    clock, folder = env
    engine = TaskEngine({"only_safe": lambda: {}}, utc_timestamp=clock.now)
    with pytest.raises(ValueError,match="unregistered"):
        engine.configure([TaskSpec("bad","shell",60)])
    with pytest.raises(ValueError,match="duplicate"):
        engine.configure([TaskSpec("dup","only_safe",30)]*2)
    with pytest.raises(ValueError):
        TaskSpec("bad", "only_safe", float("nan"))
    with pytest.raises(ValueError):
        TaskSpec("bad", "only_safe", 0)
    config = folder/"tasks.json"
    config.write_text(json.dumps({"tasks":[
        {"task_id":"fine","action":"only_safe","interval_seconds":3600},
        {"task_id":"unsafe","action":"only_safe","interval_seconds":60,
         "shell":"rm -rf /"}]}))
    with pytest.raises(ValueError,match="unknown task config fields"):
        load_task_specs(config)


def test_tick_registry_opt_in_only(env):
    clock, _ = env
    called = []
    eng = TaskEngine({"pulse": lambda: called.append(1)},
                     utc_timestamp=clock.now)
    eng.configure([TaskSpec("pulse","pulse",60)])
    default = build_default_handlers()
    assert not any(x["name"] == "bean_tasks" for x in default.summary())
    scheduled = build_default_handlers(task_engine=eng, reflection_interval=100)
    assert any(x["name"] == "bean_tasks" for x in scheduled.summary())
    # Running on tick zero also triggers built-in reflection. Instead,
    # invoke the new handler directly to isolate scheduling behavior.
    task_handler = next(h for h in scheduled._handlers if h.name=="bean_tasks")
    task_handler.fn(0,"fixture-session",{})
    assert called == [1]


def test_event_sink_does_not_trigger_duplicate_side_effects(env):
    clock, _ = env
    called = []
    def bad_sink(event):
        raise RuntimeError("downstream journal unavailable")
    eng = TaskEngine({"task":lambda: called.append(1)}, utc_timestamp=clock.now,
                     event_sink=bad_sink)
    eng.configure([TaskSpec("one","task",60)])
    # The action mutated an in-memory list but returned no receipt:
    # the scheduler must not invent a verified result. The sink failure
    # must also never trigger duplicate execution.
    assert eng.poll_due()[0]["status"] == "n/a"
    assert called == [1]
    assert eng.poll_due() == []
    assert eng.history("one")[0]["state"] == "n/a"


def test_declared_disabled_task_never_runs(env):
    clock, _ = env
    called = []
    eng = TaskEngine({"task":lambda: called.append(1)},utc_timestamp=clock.now)
    eng.configure([TaskSpec("never","task",60,enabled=False)])
    assert eng.snapshot()[0]["state"] == "paused"
    clock.advance(100)
    assert eng.poll_due() == []
    assert called == []

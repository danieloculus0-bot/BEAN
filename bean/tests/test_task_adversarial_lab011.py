"""BEAN Lab 011: adversarial conversation-derived task tests.

All cases use synthetic actors and outputs. No private dialogue, personal
information, passwords, diagnoses, or real trading events are included.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from bean.memory.store import _local, get_store, init_store
from bean.runtime.task_engine import TaskEngine, TaskSpec
from bean.runtime.watcher import BeanWatcher, WatchSpec


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 10, 12, tzinfo=timezone.utc).timestamp()

    def now(self):
        return self.t

    def forward(self, seconds):
        self.t += seconds


@pytest.fixture
def env(tmp_path):
    if getattr(_local, "conn", None):
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "stress.sqlite"))
    return Clock()


@pytest.mark.parametrize("status,expected,next_state", [
    ("verified", "success", "ready"),
    ("success", "success", "ready"),
    ("ok", "success", "ready"),
    ("completed", "success", "ready"),
    ("n/a", "n/a", "ready"),
    ("stale", "n/a", "ready"),
    ("partial", "n/a", "ready"),
    ("pending", "n/a", "ready"),
    ("unverified", "n/a", "ready"),
    ("missing", "n/a", "ready"),
    ("incomplete", "n/a", "ready"),
    ("failed", "failed", "ready"),
    ("error", "failed", "ready"),
    ("unknown", "unknown", "needs_review"),
    ("indeterminate", "unknown", "needs_review"),
    ("future_unrecognized_status", "unknown", "needs_review"),
])
def test_unverified_or_unknown_outputs_never_launder_into_success(
        env, status, expected, next_state):
    task = TaskEngine({"reader": lambda: {"status":status,"details":"fixture"}},
                      utc_timestamp=env.now)
    task.configure([TaskSpec("test","reader",120,max_attempts=3)])
    event = task.poll_due()[0]
    assert event["status"] == expected
    assert task.snapshot()[0]["state"] == next_state
    assert task.history("test")[0]["state"] == expected


@pytest.mark.parametrize("result,expected", [
    (None, "n/a"),
    ({}, "n/a"),
    ({"status":"n/a", "value":None}, "n/a"),
    ({"status":"partial", "verified_sources":1,"missing_sources":2}, "n/a"),
    ({"status":"unknown"}, "unknown"),
])
def test_absent_data_is_not_zero_or_success(env, result, expected):
    task = TaskEngine({"reader": lambda: result}, utc_timestamp=env.now)
    task.configure([TaskSpec("missing","reader",20)])
    assert task.poll_due()[0]["status"] == expected


def test_unknown_outcome_requires_review_even_after_config_reload(env):
    count = []
    task = TaskEngine({"handler":lambda: count.append(1) or {"status":"unknown"}},
                      utc_timestamp=env.now)
    task.configure([TaskSpec("uncertain","handler",10)])
    assert task.poll_due()[0]["status"] == "unknown"
    assert task.history("uncertain")[0]["state"] == "unknown"
    env.forward(1000)
    task.configure([TaskSpec("uncertain","handler",10)])
    assert task.poll_due() == []
    assert count == [1]


def test_crash_after_side_effect_before_commit_never_replays(env):
    effects = []
    task = TaskEngine({"action":lambda: effects.append("once")},
                      utc_timestamp=env.now)
    task.configure([TaskSpec("persist","action",1)])
    claimed = task._claim()
    task.actions["action"]()
    # Simulate killing the process before _finish commits a result.
    recovered = TaskEngine({"action":lambda: effects.append("twice")},
                           utc_timestamp=env.now)
    assert recovered.recover_interrupted() == 1
    recovered.configure([TaskSpec("persist","action",1)])
    env.forward(10000)
    assert recovered.poll_due() == []
    assert effects == ["once"]
    assert recovered.history("persist")[0]["state"] == "unknown"
    assert recovered.history("persist")[0]["run_id"] == claimed["run_id"]


def test_multiple_workers_atomic_claim_prevents_duplicate_run(env):
    effects = []
    task = TaskEngine({"read":lambda: effects.append("done") or {"status":"ok"}},
                      utc_timestamp=env.now)
    task.configure([TaskSpec("onlyonce","read",3600)])
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: task.poll_due(max_tasks=1), range(16)))
    assert len(effects) == 1
    assert sum(bool(r) for r in results) == 1
    assert len(task.history("onlyonce")) == 1


def test_no_unbounded_catch_up_after_month_offline(env):
    effects = []
    task = TaskEngine({"health": lambda: effects.append(1) or {"status":"verified"}},
                      utc_timestamp=env.now)
    task.configure([TaskSpec("hourly","health",3600)])
    task.poll_due()
    env.forward(86400 * 30)
    assert len(task.poll_due()) == 1
    assert task.poll_due() == []
    assert len(effects) == 2


def test_fair_batch_bound_and_task_isolation(env):
    completed = []
    actions = {f"action_{i}": (lambda j=i: completed.append(j) or {"status":"ok"})
               for i in range(12)}
    task = TaskEngine(actions,utc_timestamp=env.now)
    task.configure([TaskSpec(f"item_{i}", f"action_{i}",60) for i in range(12)])
    assert len(task.poll_due(max_tasks=5)) == 5
    assert len(task.poll_due(max_tasks=5)) == 5
    assert len(task.poll_due(max_tasks=5)) == 2
    assert len(set(completed)) == 12
    assert task.poll_due() == []


def test_backwards_clock_cannot_repeat_a_completed_task(env):
    calls = []
    task = TaskEngine({"work": lambda: calls.append(1) or {"status":"ok"}},
                      utc_timestamp=env.now)
    task.configure([TaskSpec("task","work",60)])
    task.poll_due()
    env.forward(-3600)
    assert task.poll_due() == []
    assert calls == [1]


def test_a_local_watcher_without_reports_yields_na_through_tasks(env):
    watcher = BeanWatcher(
        [WatchSpec("quality_report", ("rma_count",), recall_frequency=60)],
        reader=lambda key: None,
    )
    def check():
        results = watcher.poll_due(force=True)
        states = [v["status"] for v in results.values()]
        return {"status": "verified" if states and all(s=="verified" for s in states)
                else "n/a", "report":results}
    task = TaskEngine({"watch":check},utc_timestamp=env.now)
    task.configure([TaskSpec("watcher","watch",30)])
    assert task.poll_due()[0]["status"] == "n/a"
    receipt = json.loads(task.history("watcher")[0]["result_json"])
    assert receipt["report"]["quality_report"]["values"]["rma_count"] is None


def test_no_task_config_means_no_extra_tick_handler(env):
    from bean.runtime.tick_handlers import build_default_handlers
    assert "bean_tasks" not in [
        r["name"] for r in build_default_handlers().summary()
    ]


def test_schedule_is_a_reliability_measure_not_a_permission(env):
    # No chat message, user identity string, or trust score is ever routed
    # through the allowlisted scheduler as executable Python code.
    names = []
    task = TaskEngine({"safe_read":lambda: names.append("read")},
                      utc_timestamp=env.now)
    with pytest.raises(ValueError,match="unregistered"):
        task.configure([TaskSpec("foo","trade",60)])
    with pytest.raises(ValueError,match="unregistered"):
        task.configure([TaskSpec("foo","pet",60)])
    with pytest.raises(ValueError,match="unregistered"):
        task.configure([TaskSpec("foo","shell",60)])
    assert names == []

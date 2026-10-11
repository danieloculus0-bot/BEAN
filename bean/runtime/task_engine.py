"""BEAN Lab 011: durable, bounded, opt-in task behaviors.

This is NOT a general command runner. Tasks name registered local safe actions;
no shell, arbitrary imports, network actions, orders, or physical effectors.
The trusted host controls who may edit the local task configuration.
"""
from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional

from ..memory.store import get_store

TASK_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_task_specs (
 task_id TEXT PRIMARY KEY,
 action TEXT NOT NULL,
 interval_seconds REAL NOT NULL CHECK(interval_seconds >= 1),
 next_due_at REAL NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('ready','paused','running','needs_review')),
 attempt INTEGER NOT NULL DEFAULT 0,
 max_attempts INTEGER NOT NULL DEFAULT 3,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bean_task_runs (
 run_id TEXT PRIMARY KEY,
 task_id TEXT NOT NULL,
 scheduled_at REAL NOT NULL,
 attempt INTEGER NOT NULL,
 started_at TEXT NOT NULL,
 finished_at TEXT,
 state TEXT NOT NULL CHECK(state IN ('running','success','n/a','failed','unknown')),
 result_json TEXT,
 error TEXT,
 FOREIGN KEY(task_id) REFERENCES bean_task_specs(task_id)
);
CREATE INDEX IF NOT EXISTS idx_task_due ON bean_task_specs(state, next_due_at);
CREATE INDEX IF NOT EXISTS idx_task_history ON bean_task_runs(task_id, started_at);
"""

def _timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()

def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    action: str
    interval_seconds: float
    enabled: bool = True
    max_attempts: int = 3

    def __post_init__(self):
        for field in ("task_id", "action"):
            if not isinstance(getattr(self, field), str) or not TASK_ID.fullmatch(getattr(self, field)):
                raise ValueError(f"invalid {field}")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be boolean")
        if not isinstance(self.interval_seconds, (int, float)) or isinstance(self.interval_seconds, bool):
            raise ValueError("interval_seconds must be a number")
        if not math.isfinite(self.interval_seconds) or not 1 <= self.interval_seconds <= 86400 * 30:
            raise ValueError("interval_seconds must be 1 second to 30 days")
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be 1..5")

def load_task_specs(path: str | Path) -> list[TaskSpec]:
    """Read from a trusted *local* administrator-controlled file only."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("tasks"), list):
        raise ValueError("task config requires an object containing tasks")
    if len(raw["tasks"]) > 50:
        raise ValueError("too many tasks")
    specs = []
    for item in raw["tasks"]:
        if not isinstance(item, dict) or set(item) - {
            "task_id", "action", "interval_seconds", "enabled", "max_attempts"
        }:
            raise ValueError("unknown task config fields")
        specs.append(TaskSpec(**item))
    if len(set(x.task_id for x in specs)) != len(specs):
        raise ValueError("duplicate task id")
    return specs

class TaskEngine:
    """At-most-once automatic attempts after a crash, with explicit review.

    Side effects are never silently replayed following interrupted execution.
    Known failed attempts may be retried with bounded backoff; action authors
    must still provide idempotent behavior for those known failures.
    """
    def __init__(self, actions: Mapping[str, Callable], *,
                 utc_timestamp: Callable[[], float] = _timestamp,
                 event_sink: Optional[Callable[[dict], None]] = None):
        self.store = get_store()
        self.store._conn().executescript(SCHEMA)
        self.store.commit()
        if not actions or not all(TASK_ID.fullmatch(k) and callable(v) for k, v in actions.items()):
            raise ValueError("a valid named action allowlist is required")
        self.actions = dict(actions)
        self.now = utc_timestamp
        self.event_sink = event_sink or (lambda event: None)

    def configure(self, specs: list[TaskSpec]) -> dict:
        if not isinstance(specs, list) or len(specs) > 50:
            raise ValueError("task specification list too long")
        if len({s.task_id for s in specs}) != len(specs):
            raise ValueError("duplicate task ids")
        for spec in specs:
            if not isinstance(spec, TaskSpec) or spec.action not in self.actions:
                raise ValueError(f"unregistered task action: {getattr(spec, 'action', None)}")
        now = float(self.now())
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            configured = set()
            for spec in specs:
                configured.add(spec.task_id)
                row = conn.execute(
                    "SELECT action,interval_seconds,state FROM bean_task_specs WHERE task_id=?",
                    (spec.task_id,)).fetchone()
                state = "ready" if spec.enabled else "paused"
                if row is None:
                    conn.execute(
                        "INSERT INTO bean_task_specs "
                        "(task_id,action,interval_seconds,next_due_at,state,max_attempts,created_at,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (spec.task_id,spec.action,float(spec.interval_seconds),now,state,
                         spec.max_attempts,_iso(now),_iso(now)))
                else:
                    if row["action"] != spec.action:
                        raise ValueError("changing an existing task action requires a new task id")
                    if row["state"] in ("running","needs_review"):
                        state = row["state"]
                    next_due = now if row["interval_seconds"] != float(spec.interval_seconds) else None
                    conn.execute(
                        "UPDATE bean_task_specs SET interval_seconds=?,max_attempts=?,state=?,"
                        "next_due_at=COALESCE(?,next_due_at),updated_at=? WHERE task_id=?",
                        (float(spec.interval_seconds),spec.max_attempts,state,next_due,_iso(now),spec.task_id))
            for row in conn.execute("SELECT task_id,state FROM bean_task_specs").fetchall():
                if row["task_id"] not in configured and row["state"] == "ready":
                    conn.execute("UPDATE bean_task_specs SET state='paused',updated_at=? WHERE task_id=?",
                                 (_iso(now),row["task_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return {"configured": sorted(configured), "count": len(configured)}

    def recover_interrupted(self) -> int:
        """Do not re-execute unknown side effects after crashes/restarts."""
        now = float(self.now())
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                "SELECT task_id FROM bean_task_specs WHERE state='running'").fetchall()
            for row in rows:
                task = row["task_id"]
                conn.execute(
                    "UPDATE bean_task_runs SET state='unknown',finished_at=?,"
                    "error='interrupted; outcome cannot be established automatically' "
                    "WHERE task_id=? AND state='running'", (_iso(now),task))
                conn.execute(
                    "UPDATE bean_task_specs SET state='needs_review',updated_at=? WHERE task_id=?",
                    (_iso(now),task))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        for row in rows:
            self._emit({"task_id":row["task_id"],"status":"unknown",
                        "reason":"interrupted_requires_review"})
        return len(rows)

    def _claim(self):
        now = float(self.now())
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT task_id,action,interval_seconds,next_due_at,attempt,max_attempts "
                "FROM bean_task_specs WHERE state='ready' AND next_due_at<=? "
                "ORDER BY next_due_at,task_id LIMIT 1", (now,)).fetchone()
            if row is None:
                conn.commit()
                return None
            task = dict(row)
            run_id = str(uuid.uuid4())
            attempt = task["attempt"] + 1
            conn.execute(
                "UPDATE bean_task_specs SET state='running',attempt=?,updated_at=? WHERE task_id=?",
                (attempt,_iso(now),task["task_id"]))
            conn.execute(
                "INSERT INTO bean_task_runs "
                "(run_id,task_id,scheduled_at,attempt,started_at,state) VALUES (?,?,?,?,?,'running')",
                (run_id,task["task_id"],task["next_due_at"],attempt,_iso(now)))
            conn.commit()
            return {**task,"run_id":run_id,"attempt":attempt}
        except Exception:
            conn.rollback()
            raise

    @staticmethod
    def _outcome(result) -> str:
        """Fail-closed interpretation of task results.

        'success' means the registered action finished, NOT that arbitrary
        claims in its result have become verified real-world facts.
        """
        if result is None or result == {}:
            return "n/a"
        if not isinstance(result, dict):
            return "success"  # successful return from an allowlisted local action
        reported = str(result.get("status", "")).strip().lower()
        if reported in ("failed", "failure", "error", "invalid"):
            return "failed"
        if reported in ("unknown", "uncertain", "indeterminate"):
            return "unknown"
        if reported in ("n/a", "stale", "partial", "pending", "unverified",
                        "missing", "incomplete", "not_configured"):
            return "n/a"
        if reported in ("verified", "success", "ok", "ready", "completed"):
            return "success"
        if reported:
            return "unknown"
        # Existing built-in observability actions return structured snapshots,
        # not a status. Here success means execution, not validated contents.
        return "success"

    def _finish(self, task: dict, state: str, result=None, error=None) -> dict:
        now = float(self.now())
        # Don't try to catch up an arbitrary backlog after downtime.
        interval = float(task["interval_seconds"])
        if state == "unknown":
            new_state, next_due, attempt = "needs_review", now + interval, task["attempt"]
        elif state == "failed":
            blocked = task["attempt"] >= task["max_attempts"]
            new_state = "needs_review" if blocked else "ready"
            next_due = now + min(interval, 2 ** (task["attempt"] - 1) * 10)
            attempt = task["attempt"]
        else:
            new_state, next_due, attempt = "ready", now + interval, 0
        data = json.dumps(result, default=str) if result is not None else None
        if data is not None:
            data = data[:8192]
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "UPDATE bean_task_runs SET state=?,finished_at=?,result_json=?,error=? WHERE run_id=?",
                (state,_iso(now),data,str(error)[:1000] if error else None,task["run_id"]))
            conn.execute(
                "UPDATE bean_task_specs SET state=?,next_due_at=?,attempt=?,updated_at=? "
                "WHERE task_id=? AND state='running'",
                (new_state,next_due,attempt,_iso(now),task["task_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        event = {"task_id":task["task_id"],"action":task["action"],"run_id":task["run_id"],
                 "status":state,"next_due_at":_iso(next_due) if new_state == "ready" else None,
                 "requires_review":new_state == "needs_review"}
        self._emit(event)
        return event

    def _emit(self, event: dict):
        try:
            self.event_sink(event)
        except Exception:
            # Durable task ledger is authoritative; failures of optional event sinks
            # must not cause tasks to replay or alter their recorded outcome.
            pass

    def poll_due(self, *, max_tasks: int = 5) -> list[dict]:
        if type(max_tasks) is not int or not 1 <= max_tasks <= 50:
            raise ValueError("max_tasks must be 1..50")
        results = []
        for _ in range(max_tasks):
            task = self._claim()
            if task is None:
                break
            try:
                result = self.actions[task["action"]]()
                status = self._outcome(result)
                results.append(self._finish(task,status,result=result))
            except Exception as exc:
                results.append(self._finish(task,"failed",error=repr(exc)))
        return results

    def snapshot(self) -> list[dict]:
        return [dict(row) for row in self.store.fetchall(
            "SELECT task_id,action,interval_seconds,next_due_at,state,attempt,max_attempts "
            "FROM bean_task_specs ORDER BY task_id")]

    def history(self, task_id: str, limit: int = 20) -> list[dict]:
        if not TASK_ID.fullmatch(task_id) or not isinstance(limit,int) or not 1<=limit<=200:
            raise ValueError("invalid task history request")
        return [dict(row) for row in self.store.fetchall(
            "SELECT run_id,task_id,scheduled_at,attempt,started_at,finished_at,state,result_json,error "
            "FROM bean_task_runs WHERE task_id=? ORDER BY started_at DESC LIMIT ?",
            (task_id,limit))]

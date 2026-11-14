"""BEAN native goal autonomy: choose, act, observe, persist and reconsider.

Design adapted from the MIT-licensed AutoGPT Classic agent-loop pattern.
Original implementation, no upstream code copied. Core owns the memory.
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional

from ..cognition.goal_state import ensure_goal_table
from ..memory.store import get_store
from .task_engine import TaskEngine

SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_goal_runs (
 run_id TEXT PRIMARY KEY,
 proposal_id TEXT NOT NULL UNIQUE,
 action_type TEXT NOT NULL,
 started_at TEXT NOT NULL,
 finished_at TEXT,
 state TEXT NOT NULL CHECK(state IN ('running','success','n/a','failed','unknown')),
 decision_json TEXT NOT NULL,
 result_json TEXT,
 error TEXT,
 FOREIGN KEY(proposal_id) REFERENCES cognition_goal_proposals(proposal_id)
);
CREATE INDEX IF NOT EXISTS idx_goal_runs_action ON bean_goal_runs(action_type,state);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GoalCycle:
    """Execute persisted self-generated internal goals using registered actions.

    No shell, network, hardware or general code execution is introduced.
    The host registers real actions; the model may only propose goals.
    """

    def __init__(self, actions: Mapping[str, Callable[[dict], object]], *,
                 event_sink: Optional[Callable[[dict], None]] = None):
        if not actions or not all(isinstance(k, str) and k and callable(v)
                                  for k, v in actions.items()):
            raise ValueError("GoalCycle needs registered named handlers")
        self.actions = dict(actions)
        self.store = get_store()
        ensure_goal_table()
        self.store._conn().executescript(SCHEMA)
        self.store.commit()
        self.event_sink = event_sink or (lambda event: None)

    def recover_interrupted(self) -> int:
        """Unknown external outcomes must never be automatically replayed."""
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                "SELECT run_id,proposal_id FROM bean_goal_runs WHERE state='running'"
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE bean_goal_runs SET state='unknown',finished_at=?,"
                    "error='interrupted; effect unknown' WHERE run_id=?",
                    (_now(), row["run_id"]))
                conn.execute(
                    "UPDATE cognition_goal_proposals SET status='needs_review',"
                    "resolved_at=? WHERE proposal_id=? AND status='running'",
                    (_now(), row["proposal_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return len(rows)

    def _claim(self) -> Optional[dict]:
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Existing BEAN cognition proposes goals. Only explicit registered
            # internal operations can execute. Others remain in the ledger.
            rows = conn.execute(
                "SELECT * FROM cognition_goal_proposals "
                "WHERE status='pending' AND approval_required='none' "
                "ORDER BY priority,id LIMIT 100"
            ).fetchall()
            candidates = []
            for row in rows:
                action = row["action_type"]
                if action not in self.actions:
                    continue
                stats = conn.execute(
                    "SELECT COUNT(*) AS tries,"
                    "SUM(CASE WHEN state='success' THEN 1 ELSE 0 END) AS good,"
                    "SUM(CASE WHEN state='failed' THEN 1 ELSE 0 END) AS bad "
                    "FROM bean_goal_runs WHERE action_type=?", (action,)
                ).fetchone()
                tries, good, bad = (stats["tries"] or 0,
                                    stats["good"] or 0, stats["bad"] or 0)
                usable = good + bad
                novelty = 8.0 / math.sqrt(1 + tries)
                observed = 2.0 * (good - bad) / usable if usable else 0.0
                priority = max(1, min(9, int(row["priority"])))
                score = -100.0 * priority + novelty + observed
                candidates.append((score, -int(row["id"]), row, {
                    "policy": "priority_novelty_observed_outcomes_v1",
                    "priority": priority, "prior_attempts": tries,
                    "observed_successes": good, "observed_failures": bad,
                    "unknown_not_rewarded": True,
                    "selection_score": round(score, 6),
                }))
            if not candidates:
                conn.commit()
                return None
            _, _, row, decision = max(candidates, key=lambda x: (x[0], x[1]))
            run_id = str(uuid.uuid4())
            claimed = conn.execute(
                "UPDATE cognition_goal_proposals SET status='running' "
                "WHERE proposal_id=? AND status='pending'",
                (row["proposal_id"],))
            if claimed.rowcount != 1:
                raise RuntimeError("goal changed during atomic claim")
            conn.execute(
                "INSERT INTO bean_goal_runs "
                "(run_id,proposal_id,action_type,started_at,state,decision_json) "
                "VALUES (?,?,?,?,'running',?)",
                (run_id, row["proposal_id"], row["action_type"], _now(),
                 json.dumps(decision, sort_keys=True)))
            conn.commit()
            return {"run_id": run_id, "proposal_id": row["proposal_id"],
                    "action_type": row["action_type"],
                    "motivation": row["motivation"],
                    "goal_state": row["goal_state"],
                    "action_detail": json.loads(row["action_detail"] or "null"),
                    "decision": decision}
        except Exception:
            conn.rollback()
            raise

    def _finish(self, goal: dict, result=None, error=None) -> dict:
        state = "failed" if error is not None else TaskEngine._outcome(result)
        if state not in ("success", "n/a", "failed", "unknown"):
            state = "unknown"
        new_status = {"success": "completed", "n/a": "needs_evidence",
                      "failed": "failed", "unknown": "needs_review"}[state]
        payload = (json.dumps(result, default=str, ensure_ascii=False)[:8192]
                   if result is not None else None)
        conn = self.store._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "UPDATE bean_goal_runs SET state=?,finished_at=?,result_json=?,error=? "
                "WHERE run_id=? AND state='running'",
                (state, _now(), payload, repr(error)[:1000] if error else None,
                 goal["run_id"]))
            conn.execute(
                "UPDATE cognition_goal_proposals SET status=?,resolved_at=? "
                "WHERE proposal_id=? AND status='running'",
                (new_status, _now(), goal["proposal_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        receipt = {"run_id": goal["run_id"], "proposal_id": goal["proposal_id"],
                   "action_type": goal["action_type"], "status": state,
                   "proposal_status": new_status, "decision": goal["decision"],
                   "model_weights_trained": False,
                   "independent_outcome_verified": False}
        try:
            self.event_sink(receipt)
        except Exception:
            pass  # Durable SQLite receipt is authoritative; do not replay.
        return receipt

    def poll_due(self, *, max_goals: int = 1) -> list[dict]:
        if type(max_goals) is not int or not 1 <= max_goals <= 5:
            raise ValueError("max_goals must be 1..5")
        outcomes = []
        for _ in range(max_goals):
            goal = self._claim()
            if goal is None:
                break
            try:
                result = self.actions[goal["action_type"]](goal)
                error = None
            except Exception as exc:
                result, error = None, exc
            # An error persisting a receipt must remain visible; do not
            # mistake a storage failure for a second failed agent action.
            outcomes.append(self._finish(goal, result=result, error=error))
        return outcomes

    def history(self, limit: int = 20) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("limit must be 1..200")
        return [dict(row) for row in self.store.fetchall(
            "SELECT * FROM bean_goal_runs ORDER BY started_at DESC LIMIT ?",
            (limit,))]

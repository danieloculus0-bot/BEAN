"""Apply measured BEAN rewards to SpongeTD once, with durable checkpoint receipts.

This is a *caller-attested* evaluation interface, not a truth oracle.
Only complete matched trials earn TD updates. The SQLite reward receipt and
the SHA-chained Q checkpoint commit together in one database transaction.
"""
from __future__ import annotations

from dataclasses import asdict
import copy
import json
import sqlite3

from bean.optimization.scoreboard_context import RewardTrial, score_reward

SCHEMA = "bean.learning.measured_feedback.v1"


class MeasuredFeedback:
    def __init__(self, service):
        self.service = service
        self.db = service.policy.journal.db
        self.db.execute("""CREATE TABLE IF NOT EXISTS measured_learning_receipts (
            receipt_id TEXT PRIMARY KEY,
            episode_id TEXT NOT NULL,
            trial_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            q_step INTEGER NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        self.db.commit()

    def record(self, *, episode_id, trial, done=True, next_state=None):
        if not isinstance(trial, dict):
            raise ValueError("trial must be a structured measurement record")
        scored = score_reward(RewardTrial(**trial))
        if not scored["eligible"]:
            return {**scored, "learned": False, "new_reward": False}
        if trial["matched_cases"] < 30:
            return {**scored, "learned": False, "new_reward": False,
                    "reason": "checkpoint_requires_30_matched_cases"}
        if type(done) is not bool:
            raise ValueError("done must be boolean")
        if not done and next_state is None:
            raise ValueError("nonterminal feedback requires next_state")
        prior = self.db.execute(
            "SELECT trial_json FROM measured_learning_receipts WHERE receipt_id=?",
            (scored["receipt_id"],)).fetchone()
        if prior is not None:
            if json.loads(prior[0]) != asdict(RewardTrial(**trial)):
                raise ValueError("immutable receipt conflict")
            return {**scored, "learned": False, "new_reward": False,
                    "reason": "already_recorded"}
        episode = self.service._episodes.get(episode_id)
        if not episode or episode["pending"] is None:
            raise ValueError("measured reward requires an outstanding BEAN choice")
        # A matched score's direction determines whether positive or negative
        # raw values mean improvement. This transforms metrics only for the
        # existing score-before-checkpoint routine, not for the actual reward.
        sign = 1 if trial["direction"] == "higher" else -1
        before = copy.deepcopy(self.service.policy.q)
        before_steps = self.service.policy.steps
        episode_snapshot = dict(episode)
        receipt = {
            "schema": SCHEMA,
            "trial": asdict(RewardTrial(**trial)),
            "reward": scored,
        }
        try:
            # Same sqlite connection as SpongeTD's Journal. Its append commits
            # this receipt and the checkpoint together, or neither.
            self.db.execute(
                """INSERT INTO measured_learning_receipts
                   (receipt_id,episode_id,trial_json,result_json,q_step)
                   VALUES (?,?,?,?,?)""",
                (scored["receipt_id"], episode_id,
                 json.dumps(receipt["trial"], sort_keys=True, allow_nan=False),
                 json.dumps(receipt["reward"], sort_keys=True, allow_nan=False),
                 before_steps + 1))
            self.service.feedback(
                episode_id=episode_id, reward=scored["reward"],
                next_state=next_state, done=done)
            checkpoint = self.service.checkpoint(
                baseline=sign * trial["baseline"],
                candidate=sign * trial["candidate"],
                samples=trial["matched_cases"],
                evaluation_sha256=trial["evaluation_sha256"])
        except Exception:
            self.db.rollback()
            self.service.policy.q = before
            self.service.policy.steps = before_steps
            self.service._episodes[episode_id] = episode_snapshot
            raise
        return {
            **scored, "learned": True, "new_reward": True,
            "q_step": self.service.policy.steps,
            "durable_checkpoint": True,
            "checkpoint_sha256": checkpoint["memory_sha256"],
            "checkpoint_journal_tip": checkpoint["journal_tip"],
            "evidence_independently_verified": False,
        }

    def history(self, *, limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be within 1..100")
        rows = self.db.execute(
            """SELECT receipt_id,episode_id,trial_json,result_json,q_step,
                      recorded_at FROM measured_learning_receipts
               ORDER BY rowid DESC LIMIT ?""", (limit,)).fetchall()
        return {"schema": SCHEMA, "records": [
            {"receipt_id": row[0], "episode_id": row[1],
             "trial": json.loads(row[2]), "result": json.loads(row[3]),
             "q_step": row[4], "recorded_at": row[5]}
            for row in rows]}


def register_measured_feedback(inbox, service):
    bridge = MeasuredFeedback(service)
    inbox.register("learning_evaluated_feedback",
                   lambda msg, _: bridge.record(**msg.args))
    inbox.register("learning_reward_history",
                   lambda msg, _: bridge.history(**msg.args))
    return inbox

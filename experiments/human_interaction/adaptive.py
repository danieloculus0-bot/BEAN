"""Experimental executable online interaction policy, not an LLM or production Core wiring.

Feedback changes next-turn behavior; SQLite persists state across process restarts.
Caller-provided feedback is an observed label, not authenticated ground truth.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ACTIONS = ("exit", "correction", "clarify")
DEFAULT_Q = {"exit": 0.2, "correction": 0.0, "clarify": 0.1}


def context_key(previous_user: str, user_turn: str) -> str:
    """Abstract to features; never store raw chat text."""
    words = re.findall(r"[a-z]+", previous_user.lower())
    before = words[-1] if words else ""
    current = user_turn.strip().lower()
    if len(current.split()) == 1 and current.isalpha():
        swap = any(before == current[:i] + current[i + 1] + current[i] + current[i + 2:]
                   for i in range(len(current) - 1))
        return "single-word/preceding-transposition" if swap else "single-word/other"
    return "multiword"


class AdaptiveInteraction:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS scores (context TEXT NOT NULL, action TEXT NOT NULL, q REAL NOT NULL, observations INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(context, action))")
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, context TEXT NOT NULL, action TEXT NOT NULL, reward REAL NOT NULL, next_q REAL NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def _scores(self, context):
        rows = self.db.execute("SELECT action,q FROM scores WHERE context=?", (context,)).fetchall()
        result = dict(DEFAULT_Q)
        result.update(rows)
        return result

    def choose(self, previous_user, user_turn):
        key = context_key(previous_user, user_turn)
        scores = self._scores(key)
        # Deterministic tie breaking, honest about initial non-optimal action.
        action = max(ACTIONS, key=lambda a: (scores[a], -ACTIONS.index(a)))
        return {"context": key, "action": action, "scores": scores}

    def act(self, previous_user, user_turn):
        decision = self.choose(previous_user, user_turn)
        message = {
            "exit": "Understood. I'll leave the conversation here.",
            "correction": "I think that may be a correction of the last word, rather than a request to leave.",
            "clarify": "Is that a correction to your previous sentence, or a new request?",
        }[decision["action"]]
        return {**decision, "response": message}

    def learn(self, previous_user, user_turn, action, reward, *, alpha=0.5):
        if action not in ACTIONS or not isinstance(reward, (int, float)) or not -1 <= reward <= 1:
            raise ValueError("invalid feedback")
        if not 0 < alpha <= 1:
            raise ValueError("invalid learning rate")
        key = context_key(previous_user, user_turn)
        old = self._scores(key)[action]
        new = old + alpha * (float(reward) - old)
        with self.db:
            self.db.execute("INSERT INTO scores(context,action,q,observations) VALUES(?,?,?,1) ON CONFLICT(context,action) DO UPDATE SET q=excluded.q, observations=observations+1", (key, action, new))
            self.db.execute("INSERT INTO feedback(context,action,reward,next_q) VALUES(?,?,?,?)", (key, action, float(reward), new))
        return {"context": key, "action": action, "old_q": old, "new_q": new}

    def journal(self):
        return [dict(id=r[0], context=r[1], action=r[2], reward=r[3], next_q=r[4])
                for r in self.db.execute("SELECT id,context,action,reward,next_q FROM feedback ORDER BY id")]


def demonstrate(path):
    prior = "That damn shrimp manager can elave"
    turn = "leave"
    agent = AdaptiveInteraction(path)
    try:
        before = agent.act(prior, turn)
        correction = agent.learn(prior, turn, before["action"], -1)
        improvement = agent.learn(prior, turn, "correction", 1)
        after = agent.act(prior, turn)
        journal = agent.journal()
    finally:
        agent.close()
    restored = AdaptiveInteraction(path)
    try:
        reboot = restored.act(prior, turn)
    finally:
        restored.close()
    return {"before": before, "feedback": [correction, improvement],
            "after": after, "after_restart": reboot, "journal": journal,
            "adapted": before["action"] != after["action"] and after["action"] == reboot["action"]}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, help="Disposable SQLite file")
    args = p.parse_args()
    print(json.dumps(demonstrate(args.db), indent=2))

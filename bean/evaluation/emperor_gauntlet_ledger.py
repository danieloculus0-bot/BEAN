"""Experimental BEAN Core bridge for Emperor Gauntlet Q-learning receipts.

The game learner lives in FUN. This module imports its *observed* rewards,
per-decision encoded states, game scores and Q snapshots into BEAN's existing
SQLite memory store. No foundation-model training is claimed. Source authenticity
is not established merely by a valid local JSON receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from bean.memory.store import MemoryStore

KINDS = {"training", "random-control", "learned-holdout"}
ACTION_COUNT = 15

SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_emperor_episodes (
 receipt_sha256 TEXT PRIMARY KEY,
 source_commit TEXT NOT NULL,
 kind TEXT NOT NULL,
 seed INTEGER NOT NULL,
 kills INTEGER NOT NULL,
 wave INTEGER NOT NULL,
 return_total REAL NOT NULL,
 steps INTEGER NOT NULL,
 payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS bean_emperor_source ON bean_emperor_episodes(source_commit,kind);
CREATE TABLE IF NOT EXISTS bean_emperor_policies (
 policy_sha256 TEXT PRIMARY KEY,
 source_commit TEXT NOT NULL,
 updates INTEGER NOT NULL,
 q_states INTEGER NOT NULL,
 payload_json TEXT NOT NULL
);
"""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def validate_episode(row: dict) -> dict:
    """Ensure every scored match has reconstructible encoded decision records."""
    if not isinstance(row, dict) or row.get("kind") not in KINDS:
        raise ValueError("unsupported BEAN episode kind")
    for name in ("seed", "kills", "wave", "steps"):
        if not _nonnegative_int(row.get(name)):
            raise ValueError("invalid episode " + name)
    if not isinstance(row.get("sourceCommit"), str) or not row["sourceCommit"].strip():
        raise ValueError("source commit required")
    if type(row.get("reward")) not in (float, int) or not math.isfinite(row["reward"]):
        raise ValueError("invalid total reward")
    trace = row.get("trace")
    if not isinstance(trace, dict) or trace.get("version") != 1 or trace.get("seed") != row["seed"]:
        raise ValueError("invalid or mismatched trace header")
    states, steps = trace.get("states"), trace.get("rows")
    if not isinstance(states, list) or not states or any(not isinstance(s, str) or not s for s in states):
        raise ValueError("invalid Q state legend")
    if len(set(states)) != len(states):
        raise ValueError("duplicated Q state codes")
    if not isinstance(steps, list) or len(steps) != row["steps"] or not steps:
        raise ValueError("missing decision trace")
    last_kills = 0
    for i, event in enumerate(steps):
        if not isinstance(event, list) or len(event) != 8:
            raise ValueError(f"invalid decision at {i}")
        sid, action, reward, next_sid, done, kills, hp, temp = event
        if not (_nonnegative_int(sid) and sid < len(states) and
                _nonnegative_int(next_sid) and next_sid < len(states) and
                _nonnegative_int(action) and action < ACTION_COUNT and
                type(reward) is int and done in (0, 1) and
                _nonnegative_int(kills) and kills >= last_kills and
                type(hp) is int and type(temp) is int):
            raise ValueError(f"invalid Q transition at {i}")
        if i < len(steps)-1 and done:
            raise ValueError("premature terminal marker")
        last_kills = kills
    if last_kills != row["kills"] or steps[-1][4] != 1:
        raise ValueError("terminal scored kills do not match receipt")
    observed_reward = sum(event[2] for event in steps) / 1000
    if abs(observed_reward - row["reward"]) > .011:
        raise ValueError("recorded reward disagrees with decision trace")
    return row


def validate_policy(row: dict) -> dict:
    if not isinstance(row, dict) or row.get("version") != 1:
        raise ValueError("unsupported Q policy version")
    if not _nonnegative_int(row.get("updates")):
        raise ValueError("invalid learned updates")
    table = row.get("table")
    if not isinstance(table, dict):
        raise ValueError("missing learned action-value table")
    for key, values in table.items():
        if not isinstance(key, str) or not key:
            raise ValueError("invalid Q state")
        if not isinstance(values, list) or len(values) != ACTION_COUNT or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("invalid Q action vector")
    return row


def import_ledger(store: MemoryStore, filename: str | Path) -> dict:
    """Idempotent, append-only ingestion. No past episode is silently replaced."""
    store.execute(SCHEMA.split("CREATE INDEX")[0])
    # exec() forbids multiple SQL statements. Create remaining schema explicitly.
    store.execute("CREATE INDEX IF NOT EXISTS bean_emperor_source ON bean_emperor_episodes(source_commit,kind)")
    store.execute("""CREATE TABLE IF NOT EXISTS bean_emperor_policies (
     policy_sha256 TEXT PRIMARY KEY, source_commit TEXT NOT NULL, updates INTEGER NOT NULL,
     q_states INTEGER NOT NULL, payload_json TEXT NOT NULL)""")
    rows = Path(filename).read_text(encoding="utf-8").splitlines()
    count = 0
    for line in rows:
        if not line.strip():
            continue
        episode = validate_episode(json.loads(line))
        encoded = _canonical(episode)
        digest = _sha(episode)
        if store.fetchone("SELECT receipt_sha256 FROM bean_emperor_episodes WHERE receipt_sha256=?", (digest,)):
            continue
        store.execute(
            "INSERT INTO bean_emperor_episodes VALUES (?,?,?,?,?,?,?,?,?)",
            (digest, episode["sourceCommit"], episode["kind"], episode["seed"],
             episode["kills"], episode["wave"], episode["reward"], episode["steps"], encoded))
        count += 1
    store.commit()
    return {"imported": count, "total_lines": len(rows)}


def import_policy(store: MemoryStore, filename: str | Path, source_commit: str) -> str:
    policy = validate_policy(json.loads(Path(filename).read_text(encoding="utf-8")))
    digest = _sha(policy)
    store.execute("""CREATE TABLE IF NOT EXISTS bean_emperor_policies (
     policy_sha256 TEXT PRIMARY KEY, source_commit TEXT NOT NULL, updates INTEGER NOT NULL,
     q_states INTEGER NOT NULL, payload_json TEXT NOT NULL)""")
    store.execute("INSERT OR IGNORE INTO bean_emperor_policies VALUES (?,?,?,?,?)",
                  (digest, source_commit, policy["updates"], len(policy["table"]), _canonical(policy)))
    store.commit()
    return digest


def scoreboard(store: MemoryStore, source_commit: str) -> dict:
    """Read only one game build; never mix incompatible cohorts silently."""
    if not source_commit:
        raise ValueError("select a source commit")
    rows = store.fetchall(
        "SELECT kind,kills FROM bean_emperor_episodes WHERE source_commit=? ORDER BY rowid",
        (source_commit,))
    grouped = {kind: [r["kills"] for r in rows if r["kind"] == kind] for kind in KINDS}
    def mean(key: str):
        values = grouped[key]
        return sum(values)/len(values) if values else None
    policies = store.fetchall(
        "SELECT policy_sha256,updates,q_states FROM bean_emperor_policies WHERE source_commit=? ORDER BY rowid",
        (source_commit,))
    return {
        "source_commit": source_commit,
        "training_episodes": len(grouped["training"]),
        "best_training_kills": max(grouped["training"], default=None),
        "average_training_kills": mean("training"),
        "random_control_episodes": len(grouped["random-control"]),
        "random_control_mean": mean("random-control"),
        "learned_holdout_episodes": len(grouped["learned-holdout"]),
        "learned_holdout_mean": mean("learned-holdout"),
        "policy_receipts": [dict(r) for r in policies],
        "limitations": "Observational arcade results; no model-weight or generalized cognitive learning claim."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="BEAN Emperor Gauntlet Q-ledger bridge")
    parser.add_argument("--db", required=True, help="existing or new BEAN memory SQLite path")
    parser.add_argument("--ingest", type=Path, help="CI bean-emperor-episode-ledger.jsonl")
    parser.add_argument("--policy", type=Path, help="CI bean-emperor-trained-policy.json")
    parser.add_argument("--source-commit", required=True, help="exact game source SHA, or local")
    args = parser.parse_args()
    store = MemoryStore(args.db)
    try:
        if args.ingest:
            print("ingest:", json.dumps(import_ledger(store, args.ingest)))
        if args.policy:
            print("policy:", import_policy(store, args.policy, args.source_commit))
        print(json.dumps(scoreboard(store, args.source_commit), indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()

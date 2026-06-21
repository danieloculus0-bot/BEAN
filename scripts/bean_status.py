#!/usr/bin/env python3
"""Print a compact BEAN brain/runtime status from the SQLite DB."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def load_env(path: str = "/etc/bean/bean.env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def scalar(conn: sqlite3.Connection, sql: str, params=()):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return bool(scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)))


def main() -> int:
    load_env()
    db_path = Path(os.environ.get("BEAN_DB_PATH", "/home/bean/bean_data/bean_memory.db"))
    if not db_path.exists():
        print(f"BEAN DB not found: {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    sessions = scalar(conn, "SELECT COUNT(*) FROM sessions") or 0
    events = scalar(conn, "SELECT COUNT(*) FROM events") or 0
    active_session = conn.execute("SELECT session_uuid, boot_time FROM sessions WHERE shutdown_time IS NULL ORDER BY id DESC LIMIT 1").fetchone()
    active_claims = scalar(conn, "SELECT COUNT(*) FROM world_claims WHERE active=1") if table_exists(conn, "world_claims") else 0
    uncertainties = scalar(conn, "SELECT COUNT(*) FROM world_claims WHERE active=1 AND category='uncertainty'") if table_exists(conn, "world_claims") else 0
    drives = scalar(conn, "SELECT COUNT(*) FROM cognition_drive_states") if table_exists(conn, "cognition_drive_states") else 0
    proposals = scalar(conn, "SELECT COUNT(*) FROM cognition_goal_proposals WHERE status='pending'") if table_exists(conn, "cognition_goal_proposals") else 0
    states = scalar(conn, "SELECT COUNT(*) FROM cognition_possibility_states WHERE active=1") if table_exists(conn, "cognition_possibility_states") else 0

    print("BEAN Brain Status")
    print(f"DB: {db_path}")
    print(f"sessions: {sessions}")
    print(f"events: {events}")
    print(f"active_session: {active_session['session_uuid'][:8] if active_session else 'none'}")
    print(f"active_claims: {active_claims}")
    print(f"uncertainties: {uncertainties}")
    print(f"drive_rows: {drives}")
    print(f"pending_proposals: {proposals}")
    print(f"active_possibility_states: {states}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

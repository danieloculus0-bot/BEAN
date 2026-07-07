"""Origin covenant persistence smoke test."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.identity import bootstrap_identity
from bean.memory.origin import ORIGIN_KEY, ensure_origin_records
from bean.memory.session import begin_session
from bean.memory.store import _local, get_store, init_store


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    init_store(str(tmpdir / "origin_covenant.db"))
    bootstrap_identity()
    return begin_session()


def test_origin_covenant_is_persisted_and_idempotent():
    session_uuid = make_db()
    first = ensure_origin_records(session_uuid)
    second = ensure_origin_records(session_uuid)
    assert first["created"] is True
    assert second["created"] is False
    row = get_store().fetchone("SELECT version, change_summary FROM developmental_history WHERE version=?", (ORIGIN_KEY,))
    assert row is not None
    assert "origin covenant" in row["change_summary"].lower()
    summary = get_store().fetchone("SELECT summary_type, content FROM continuity_summaries WHERE summary_type='origin_covenant'")
    assert summary is not None
    assert "BEAN" in summary["content"]


if __name__ == "__main__":
    try:
        test_origin_covenant_is_persisted_and_idempotent()
        print("PASS test_origin_covenant_is_persisted_and_idempotent")
    except Exception:
        print("FAIL test_origin_covenant_is_persisted_and_idempotent")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)

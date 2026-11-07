"""Origin covenant persistence smoke test."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bean.memory.identity import bootstrap_identity, get_identity
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
    # The original digital-first research mission is not newly discovered on each boot.
    assert "digital" in summary["content"].lower()
    assert "github" in summary["content"].lower()
    assert "consciousness" in summary["content"].lower()
    assert "digital" in first["origin"]["digital_experience_rule"].lower()
    identity = get_identity()
    assert "body-optional" in identity["what_bean_is"]
    assert "GitHub supports delayed" in identity["what_bean_is"]





def test_earlier_origin_version_is_preserved_when_mission_record_is_updated():
    session_uuid = make_db()
    store = get_store()
    # A historical mission covenant is evidence and must not be overwritten.
    store.execute(
        "INSERT INTO developmental_history "
        "(version, change_summary, reason, changed_by, files_affected) "
        "VALUES (?, ?, ?, ?, ?)",
        ("BEAN_ORIGIN_COVENANT_002", "historical covenant", "prior version",
         "system_bootstrap", "[]"),
    )
    store.commit()
    assert ensure_origin_records(session_uuid)["created"] is True
    assert ensure_origin_records(session_uuid)["created"] is False
    history = store.fetchall(
        "SELECT version, change_summary FROM developmental_history "
        "WHERE version IN (?, ?) ORDER BY version",
        ("BEAN_ORIGIN_COVENANT_002", ORIGIN_KEY),
    )
    assert len(history) == 2
    assert history[0]["change_summary"] == "historical covenant"
    assert history[1]["version"] == ORIGIN_KEY
    assert store.fetchone(
        "SELECT COUNT(*) AS count FROM continuity_summaries "
        "WHERE summary_type='origin_covenant'"
    )["count"] == 1

if __name__ == "__main__":
    try:
        test_origin_covenant_is_persisted_and_idempotent()
        test_earlier_origin_version_is_preserved_when_mission_record_is_updated()
        print("PASS origin covenant mission and migration")
    except Exception:
        print("FAIL test_origin_covenant_is_persisted_and_idempotent")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)

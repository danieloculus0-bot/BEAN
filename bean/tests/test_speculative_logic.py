"""Brain 0.13 hypothesis smoke tests."""

import tempfile
from pathlib import Path

from bean.memory.store import init_store, _local
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session


def make_db():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close(); _local.conn = None
    tmpdir = Path(tempfile.mkdtemp())
    store = init_store(str(tmpdir / "hypothesis.db"))
    bootstrap_identity()
    return store._conn(), begin_session()


def test_hypothesis_creation_and_summary():
    conn, session_uuid = make_db()
    from bean.speculation import init_speculation
    engine = init_speculation(conn)
    created = engine.create_hypothesis(session_uuid, "This might become useful.", claim_type="hypothesis", evidence_level="hypothetical")
    assert created["hypothesis_id"]
    summary = engine.build_speculative_summary(session_uuid)
    assert summary["unresolved_count"] == 1


def test_non_fact_claim_not_observed():
    conn, session_uuid = make_db()
    from bean.speculation import init_speculation
    engine = init_speculation(conn)
    try:
        engine.create_hypothesis(session_uuid, "This might be true.", claim_type="speculation", evidence_level="observed")
        assert False
    except ValueError:
        assert True


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name](); print(f"PASS {name}")
        except Exception:
            failed += 1; print(f"FAIL {name}"); import traceback; traceback.print_exc()
    raise SystemExit(1 if failed else 0)

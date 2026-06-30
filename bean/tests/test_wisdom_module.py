"""Brain 0.9 wisdom module tests."""

from __future__ import annotations

import sqlite3

from bean.wisdom import evaluate_text_for_wisdom, init_wisdom_schema, seed_default_triggers, wisdom_counts

SESSION = "wisdom_test_session"


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_wisdom_schema(conn)
    return conn


def test_seed_default_triggers():
    conn = make_conn()
    inserted = seed_default_triggers(conn)
    assert inserted >= 1
    counts = wisdom_counts(conn)
    assert counts["wisdom_triggers"] >= 1


def test_wisdom_activation_records_trace_and_frame():
    conn = make_conn()
    seed_default_triggers(conn)
    result = evaluate_text_for_wisdom(conn, SESSION, "I feel certain maybe move now", source="test")
    assert result["activated"] is True
    assert result["motion_enabled"] is False
    assert result["sentience_claimed"] is False
    counts = wisdom_counts(conn)
    assert counts["wisdom_activation_traces"] >= 1
    assert counts["wisdom_meaning_frames"] >= 1


if __name__ == "__main__":
    tests = [name for name in globals() if name.startswith("test_")]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
            import traceback
            traceback.print_exc()
    print(f"{len(tests) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

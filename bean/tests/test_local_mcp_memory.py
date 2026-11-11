"""Actual BEAN Core local MCP memory regression, without optional MCP SDK.

Tests the canonical SQLite event and JSONL audit mirror, repeat-session
continuity, refusal on missing memory, age/window and source provenance.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bean.integration.local_mcp_memory import (
    ACTIVE_HOURS, _current, _path, recall, remember, status,
)


class LocalMCPMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bean-mcp-memory-")
        self.db = Path(self.tmp.name) / "local.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_sqlite_note_across_distinct_core_sessions(self):
        first = remember("Project color", "We selected orange.", database=self.db)
        self.assertTrue(first["saved"])
        self.assertFalse(first["verified_fact"])
        self.assertEqual(first["persistence"], "real_bean_core_sqlite_and_jsonl_mirror")
        result = recall("What color is the project?", database=self.db)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["note"], "We selected orange.")
        self.assertFalse(result["conflicting_notes"])
        self.assertTrue((Path(str(self.db.resolve()) + ".events.jsonl")).is_file())
        info = status(database=self.db)
        self.assertEqual(info["records_active"], 1)
        self.assertGreaterEqual(info["core_sessions"], 3)
        self.assertEqual(info["memory_window_hours"], ACTIVE_HOURS)
        self.assertEqual(info["verified_facts"], 0)

    def test_conflicts_and_no_invented_memory(self):
        remember("Favorite demo color", "Mint green.", database=self.db)
        remember("Favorite demo color", "Orange.", database=self.db)
        found = recall("demo color", database=self.db)
        self.assertEqual(found["count"], 2)
        self.assertTrue(found["conflicting_notes"])
        none = recall("nonexistent submarine", database=self.db)
        self.assertTrue(none["no_matching_memory"])
        self.assertEqual(none["matches"], [])
        self.assertEqual(none["fact_verification"], "not_performed")

    def test_invalid_inputs_and_database_required(self):
        with self.assertRaises(ValueError):
            remember("Too long", "x" * 701, database=self.db)
        with self.assertRaises(ValueError):
            recall("color", limit=0, database=self.db)
        with self.assertRaises(ValueError):
            _path("relative.sqlite")
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                _path(None)
        self.assertFalse(self.db.exists())  # failures never create state

    def test_stale_notes_are_not_recalled_as_fresh(self):
        now = datetime.now(timezone.utc)
        fixture = [
            {"created_at": (now-timedelta(hours=ACTIVE_HOURS+1)).isoformat()},
            {"created_at": (now-timedelta(hours=ACTIVE_HOURS-1)).isoformat()},
        ]
        self.assertEqual(len(_current(fixture, now)), 1)

    def test_integrity_tampering_fails_next_core_boot(self):
        remember("Protocol name", "BEAN Core.", database=self.db)
        # Direct modification to SQLite without updating the authoritative
        # mirror must be detected on the next Core startup.
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.db)) as conn:
            with conn:
                conn.execute(
                    "UPDATE events SET summary='forged' WHERE subtype=?",
                    ("local_mcp_memory_v1",),
                )
        with self.assertRaises(Exception):
            status(database=self.db)


if __name__ == "__main__":
    unittest.main()

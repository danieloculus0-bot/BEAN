"""Negative control: BEAN JSONL mirror omits SQLite correction links.

This test documents a missing evidence field. It does not alter production
memory or prove the full Core runtime behaves identically.
"""
import json
import sqlite3
import unittest


class MirrorCorrectionVisibilityTest(unittest.TestCase):
    def test_supersession_is_invisible_to_current_mirror_projection(self):
        # Reproduces the selected columns in audit_mirror._canonical_lines.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE events (
            id INTEGER PRIMARY KEY, session_uuid TEXT, event_uuid TEXT,
            event_type TEXT, subtype TEXT, summary TEXT, data TEXT,
            source TEXT, severity TEXT, created_at TEXT, superseded_by INTEGER)""")
        for i in (1, 2):
            conn.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (i, "synthetic", f"synthetic-{i}", "fact_learned",
                          None, f"fictional fact {i}", None, "system", "info",
                          "2026-01-01T00:00:00Z", None))

        def projection():
            rows = conn.execute(
                "SELECT id, session_uuid, event_uuid, event_type, subtype, "
                "summary, data, source, severity, created_at FROM events ORDER BY id"
            ).fetchall()
            return [json.dumps({
                "id": r["id"], "session_uuid": r["session_uuid"],
                "event_uuid": r["event_uuid"], "event_type": r["event_type"],
                "subtype": r["subtype"], "summary": r["summary"],
                "source": r["source"], "severity": r["severity"],
                "data": None, "ts": r["created_at"]
            }, sort_keys=True, separators=(",", ":")) for r in rows]

        before = projection()
        conn.execute("UPDATE events SET superseded_by=2 WHERE id=1")
        conn.commit()
        after = projection()
        self.assertEqual(before, after)
        self.assertEqual(conn.execute(
            "SELECT superseded_by FROM events WHERE id=1").fetchone()[0], 2)
        self.assertNotIn("superseded_by", json.loads(after[0]))
        conn.close()


if __name__ == "__main__":
    unittest.main()

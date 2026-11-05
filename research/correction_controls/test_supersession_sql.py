"""Synthetic SQL-level falsification of event correction overwrite behavior.

This test reproduces the mainline UPDATE and compares it with a guarded
conditional UPDATE under the same SQLite conditions. It does not run the
actual Core event logger or validate JSONL mirror receipts.
Run: python -m unittest -v research.correction_controls.test_supersession_sql
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

BASELINE = "UPDATE events SET superseded_by = ? WHERE id = ?"
GUARDED = ( "UPDATE events SET superseded_by = ? WHERE id = ? "
            "AND superseded_by IS NULL AND id < ? "
            "AND EXISTS (SELECT 1 FROM events WHERE id = ?)" )


class SupersessionSQLControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "events.sqlite")
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, superseded_by INTEGER)")
        self.conn.executemany("INSERT INTO events(id) VALUES (?)", [(1,), (2,), (3,)])
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def guarded(self, source, target):
        cursor = self.conn.execute(GUARDED, (target, source, target, target))
        self.conn.commit()
        return cursor.rowcount

    def test_mainline_sql_can_overwrite_a_prior_correction(self):
        self.conn.execute(BASELINE, (2, 1))
        self.conn.execute(BASELINE, (3, 1))
        self.conn.commit()
        self.assertEqual(self.conn.execute(
            "SELECT superseded_by FROM events WHERE id=1").fetchone()[0], 3)

    def test_guarded_sql_preserves_first_correction_after_restart(self):
        self.assertEqual(self.guarded(1, 2), 1)
        self.conn.close()
        self.conn = sqlite3.connect(self.path)
        self.assertEqual(self.guarded(1, 3), 0)
        self.assertEqual(self.conn.execute(
            "SELECT superseded_by FROM events WHERE id=1").fetchone()[0], 2)

    def test_guarded_sql_rejects_missing_and_backward_targets(self):
        self.assertEqual(self.guarded(1, 99), 0)
        self.assertEqual(self.guarded(2, 1), 0)
        self.assertEqual(self.guarded(1, 2), 1)

    def test_guarded_sql_rejects_missing_source(self):
        self.assertEqual(self.guarded(99, 100), 0)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE superseded_by IS NOT NULL").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

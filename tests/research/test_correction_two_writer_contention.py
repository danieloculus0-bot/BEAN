"""Synthetic two-writer correction race, not a production Core integration test."""
import sqlite3
import tempfile
import unittest
from pathlib import Path


class CorrectionConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'events.sqlite'
        self.a = sqlite3.connect(self.path, timeout=1, isolation_level=None)
        self.b = sqlite3.connect(self.path, timeout=1, isolation_level=None)
        self.a.execute('PRAGMA journal_mode=WAL')
        self.a.execute('CREATE TABLE events(id INTEGER PRIMARY KEY, superseded_by INTEGER REFERENCES events(id))')
        self.a.executemany('INSERT INTO events(id) VALUES (?)', [(1,), (2,), (3,)])

    def tearDown(self):
        self.a.close()
        self.b.close()
        self.tmp.cleanup()

    def test_unconditional_sequential_writers_overwrite(self):
        self.a.execute('UPDATE events SET superseded_by=2 WHERE id=1')
        self.b.execute('UPDATE events SET superseded_by=3 WHERE id=1')
        self.assertEqual(self.a.execute('SELECT superseded_by FROM events WHERE id=1').fetchone()[0], 3)

    def test_compare_and_swap_preserves_first_writer(self):
        self.assertEqual(self.a.execute('UPDATE events SET superseded_by=2 WHERE id=1 AND superseded_by IS NULL').rowcount, 1)
        self.assertEqual(self.b.execute('UPDATE events SET superseded_by=3 WHERE id=1 AND superseded_by IS NULL').rowcount, 0)
        self.assertEqual(self.b.execute('SELECT superseded_by FROM events WHERE id=1').fetchone()[0], 2)

    def test_active_writer_lock_requires_retry_not_silent_success(self):
        self.a.execute('BEGIN IMMEDIATE')
        self.a.execute('UPDATE events SET superseded_by=2 WHERE id=1 AND superseded_by IS NULL')
        self.b.execute('PRAGMA busy_timeout=1')
        with self.assertRaises(sqlite3.OperationalError):
            self.b.execute('UPDATE events SET superseded_by=3 WHERE id=1 AND superseded_by IS NULL')
        self.a.execute('COMMIT')
        self.assertEqual(self.b.execute('UPDATE events SET superseded_by=3 WHERE id=1 AND superseded_by IS NULL').rowcount, 0)

    def test_restart_retains_winner(self):
        self.a.execute('UPDATE events SET superseded_by=2 WHERE id=1 AND superseded_by IS NULL')
        self.a.close()
        self.b.close()
        with sqlite3.connect(self.path) as restarted:
            self.assertEqual(restarted.execute('SELECT superseded_by FROM events WHERE id=1').fetchone()[0], 2)
        self.a = sqlite3.connect(self.path)
        self.b = sqlite3.connect(self.path)


if __name__ == '__main__':
    unittest.main()

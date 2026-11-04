"""Research-only SQLite crash-window test for BEAN correction receipts.

Synthetic fixture. No BEAN runtime, hardware or production database accessed.
Run: python -m unittest -v test_correction_outbox_atomicity.py
"""
import sqlite3
import unittest


def db():
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE events (id INTEGER PRIMARY KEY, superseded_by INTEGER)')
    connection.execute('CREATE TABLE correction_receipts (id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, replacement_id INTEGER NOT NULL, UNIQUE(source_id, replacement_id))')
    connection.executemany('INSERT INTO events(id) VALUES (?)', [(1,), (2,)])
    connection.commit()
    return connection


def naive_two_commits(conn, crash=False):
    conn.execute('UPDATE events SET superseded_by=2 WHERE id=1 AND superseded_by IS NULL')
    conn.commit()
    if crash:
        raise RuntimeError('synthetic crash after first commit')
    conn.execute('INSERT INTO correction_receipts(source_id,replacement_id) VALUES (1,2)')
    conn.commit()


def atomic_correction(conn, crash=False):
    with conn:
        cursor = conn.execute('UPDATE events SET superseded_by=2 WHERE id=1 AND superseded_by IS NULL')
        if cursor.rowcount != 1:
            raise ValueError('already corrected')
        if crash:
            raise RuntimeError('synthetic crash before receipt insertion')
        conn.execute('INSERT INTO correction_receipts(source_id,replacement_id) VALUES (1,2)')


class CorrectionOutboxAtomicity(unittest.TestCase):
    def test_two_commits_leave_missing_receipt_after_crash(self):
        conn = db()
        with self.assertRaises(RuntimeError):
            naive_two_commits(conn, crash=True)
        self.assertEqual(conn.execute('SELECT superseded_by FROM events WHERE id=1').fetchone()[0], 2)
        self.assertEqual(conn.execute('SELECT count(*) FROM correction_receipts').fetchone()[0], 0)

    def test_one_transaction_rolls_back_both_on_failure(self):
        conn = db()
        with self.assertRaises(RuntimeError):
            atomic_correction(conn, crash=True)
        self.assertIsNone(conn.execute('SELECT superseded_by FROM events WHERE id=1').fetchone()[0])
        self.assertEqual(conn.execute('SELECT count(*) FROM correction_receipts').fetchone()[0], 0)

    def test_one_transaction_commits_both_and_survives_restart(self):
        conn = db()
        atomic_correction(conn)
        dump = '\n'.join(conn.iterdump())
        restored = sqlite3.connect(':memory:')
        restored.executescript(dump)
        self.assertEqual(restored.execute('SELECT superseded_by FROM events WHERE id=1').fetchone()[0], 2)
        self.assertEqual(restored.execute('SELECT source_id,replacement_id FROM correction_receipts').fetchone(), (1, 2))

    def test_duplicate_correction_rejected_without_new_receipt(self):
        conn = db()
        atomic_correction(conn)
        with self.assertRaises(ValueError):
            atomic_correction(conn)
        self.assertEqual(conn.execute('SELECT count(*) FROM correction_receipts').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()

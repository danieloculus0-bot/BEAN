"""Synthetic SQLite supersession negative control. No BEAN runtime/database access.

Run: python -m unittest discover -s research -p 'test_supersession_cas_control.py' -v
Main's unconditional UPDATE is a reproduced negative control, not a safe API.
"""
import sqlite3
import unittest


def fixture():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE events(id INTEGER PRIMARY KEY, superseded_by INTEGER)")
    db.executemany("INSERT INTO events(id) VALUES (?)", [(1,), (2,), (3,)])
    return db


def unconditional(db, old, new):
    return db.execute(
        "UPDATE events SET superseded_by=? WHERE id=?", (new, old)
    ).rowcount


def compare_and_swap(db, old, new):
    return db.execute(
        """UPDATE events SET superseded_by=?
           WHERE id=? AND superseded_by IS NULL AND id < ?
           AND EXISTS (SELECT 1 FROM events WHERE id=?)""",
        (new, old, new, new),
    ).rowcount


class SupersessionAtomicity(unittest.TestCase):
    def test_unconditional_overwrites_negative_control(self):
        db = fixture()
        self.assertEqual(unconditional(db, 1, 2), 1)
        self.assertEqual(unconditional(db, 1, 3), 1)
        self.assertEqual(db.execute(
            "SELECT superseded_by FROM events WHERE id=1"
        ).fetchone()[0], 3)

    def test_guard_preserves_first_correction(self):
        db = fixture()
        self.assertEqual(compare_and_swap(db, 1, 2), 1)
        self.assertEqual(compare_and_swap(db, 1, 3), 0)
        self.assertEqual(db.execute(
            "SELECT superseded_by FROM events WHERE id=1"
        ).fetchone()[0], 2)

    def test_guard_rejects_invalid_targets(self):
        for old, new in [(1, 99), (2, 1), (2, 2)]:
            with self.subTest(old=old, new=new):
                db = fixture()
                self.assertEqual(compare_and_swap(db, old, new), 0)

    def test_guard_allows_forward_chain(self):
        db = fixture()
        self.assertEqual(compare_and_swap(db, 1, 2), 1)
        self.assertEqual(compare_and_swap(db, 2, 3), 1)
        self.assertEqual(list(db.execute(
            "SELECT superseded_by FROM events ORDER BY id"
        )), [(2,), (3,), (None,)])


if __name__ == "__main__":
    unittest.main()

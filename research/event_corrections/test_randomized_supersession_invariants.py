"""Seeded synthetic state-machine checks for SQLite event correction links.

Research-only. Does not operate on a production BEAN memory database.
"""
import random
import sqlite3
import unittest

SEED = 20261104
STEPS = 400


def database():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, superseded_by INTEGER REFERENCES events(id))")
    conn.executemany("INSERT INTO events(id) VALUES (?)", [(i,) for i in range(1, 33)])
    conn.commit()
    return conn


def guarded(conn, old, new):
    cursor = conn.execute("""UPDATE events SET superseded_by=? WHERE id=?
        AND ? > id AND superseded_by IS NULL
        AND EXISTS (SELECT 1 FROM events WHERE id=?)""", (new, old, new, new))
    conn.commit()
    return cursor.rowcount == 1


def invariants(conn):
    rows = conn.execute("SELECT id,superseded_by FROM events ORDER BY id").fetchall()
    return all(target is None or target > source for source, target in rows)


class SupersessionStateMachine(unittest.TestCase):
    def test_seeded_mutations_preserve_monotonic_links(self):
        rng = random.Random(SEED)
        conn = database()
        model = {}
        accepted = rejected = 0
        for step in range(STEPS):
            old, new = rng.randint(-2, 35), rng.randint(-2, 35)
            expected = 1 <= old <= 32 and 1 <= new <= 32 and new > old and old not in model
            actual = guarded(conn, old, new)
            self.assertEqual(actual, expected, (step, old, new))
            if actual:
                model[old] = new
                accepted += 1
            else:
                rejected += 1
            self.assertTrue(invariants(conn))
        self.assertGreater(accepted, 0)
        self.assertGreater(rejected, 0)
        self.assertEqual(dict(conn.execute("SELECT id,superseded_by FROM events WHERE superseded_by IS NOT NULL")), model)
        snapshot = "\n".join(conn.iterdump())
        restarted = sqlite3.connect(":memory:")
        restarted.executescript(snapshot)
        self.assertEqual(list(conn.execute("SELECT * FROM events")), list(restarted.execute("SELECT * FROM events")))

    def test_unconditional_baseline_violates_invariant(self):
        conn = database()
        conn.execute("UPDATE events SET superseded_by=1 WHERE id=3")
        conn.commit()
        self.assertFalse(invariants(conn))

    def test_rejected_overwrite_preserves_first_correction(self):
        conn = database()
        self.assertTrue(guarded(conn, 2, 5))
        self.assertFalse(guarded(conn, 2, 6))
        self.assertEqual(conn.execute("SELECT superseded_by FROM events WHERE id=2").fetchone()[0], 5)


if __name__ == "__main__":
    unittest.main()

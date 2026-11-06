"""Synthetic tests for write-time correction integrity; no live BEAN database."""
import sqlite3
import unittest
from unittest.mock import patch

from bean.memory.event_logger import supersede_event


class SyntheticStore:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("""CREATE TABLE events (
            id INTEGER PRIMARY KEY, superseded_by INTEGER REFERENCES events(id))""")
        self.db.executemany("INSERT INTO events(id) VALUES (?)", [(1,), (2,), (3,)])
        self.db.commit()

    def execute(self, sql, params):
        return self.db.execute(sql, params)

    def commit(self):
        self.db.commit()

    def links(self):
        return self.db.execute("SELECT id, superseded_by FROM events ORDER BY id").fetchall()


class SupersessionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.store = SyntheticStore()
        self.patch = patch("bean.memory.event_logger.get_store", return_value=self.store)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.store.db.close)

    def test_forward_link_survives_reopen(self):
        supersede_event(1, 2)
        self.store.db.commit()
        self.assertEqual(self.store.links()[0], (1, 2))

    def test_overwrite_rejected_and_first_link_retained(self):
        supersede_event(1, 2)
        with self.assertRaises(ValueError):
            supersede_event(1, 3)
        self.assertEqual(self.store.links()[0], (1, 2))

    def test_reverse_and_self_links_rejected(self):
        for a, b in [(2, 1), (2, 2), (3, 1)]:
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                supersede_event(a, b)
        self.assertTrue(all(link is None for _, link in self.store.links()))

    def test_missing_source_and_target_rejected(self):
        for a, b in [(4, 5), (1, 5)]:
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                supersede_event(a, b)
        self.assertTrue(all(link is None for _, link in self.store.links()))

    def test_transitive_forward_chain_allowed(self):
        supersede_event(1, 2)
        supersede_event(2, 3)
        self.assertEqual(self.store.links(), [(1, 2), (2, 3), (3, None)])

    def test_noninteger_ids_rejected(self):
        for a, b in [(True, 2), (1, 2.0), (0, 2), (-1, 2)]:
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                supersede_event(a, b)


if __name__ == "__main__":
    unittest.main()

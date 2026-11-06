"""Integration regression for guarded Core event supersession.

Run: python -m unittest discover -s tests -p 'test_event_supersession_cas.py'
Uses only synthetic events and a disposable SQLite database.
"""
import tempfile
import unittest
from pathlib import Path

from bean.memory.store import init_store, get_store
from bean.memory.event_logger import EventType, log_event, supersede_event


class SupersessionCASTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        init_store(str(Path(self.temp.name) / "memory.db"))
        self.session = "synthetic-correction-test"

    def tearDown(self):
        get_store().close()
        self.temp.cleanup()

    def event(self, summary):
        return log_event(self.session, EventType.OBSERVATION, summary)

    def test_first_correction_persists_across_reopen(self):
        first, second = self.event("initial"), self.event("corrected")
        supersede_event(first, second)
        self.assertEqual(get_store().fetchone(
            "SELECT superseded_by FROM events WHERE id=?", (first,)
        )["superseded_by"], second)
        init_store(str(Path(self.temp.name) / "memory.db"))
        self.assertEqual(get_store().fetchone(
            "SELECT superseded_by FROM events WHERE id=?", (first,)
        )["superseded_by"], second)

    def test_correction_cannot_be_overwritten(self):
        first, second, third = (self.event(s) for s in ("a", "b", "c"))
        supersede_event(first, second)
        with self.assertRaises(ValueError):
            supersede_event(first, third)
        self.assertEqual(get_store().fetchone(
            "SELECT superseded_by FROM events WHERE id=?", (first,)
        )["superseded_by"], second)

    def test_missing_and_backward_corrections_rejected(self):
        first, second = self.event("a"), self.event("b")
        for original, replacement in ((first, 99999), (second, first),
                                      (first, first), (99999, 100000)):
            with self.subTest(original=original, replacement=replacement):
                with self.assertRaises(ValueError):
                    supersede_event(original, replacement)
        self.assertIsNone(get_store().fetchone(
            "SELECT superseded_by FROM events WHERE id=?", (first,)
        )["superseded_by"])


if __name__ == "__main__":
    unittest.main()

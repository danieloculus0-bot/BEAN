"""Synthetic correction-receipt restart and divergence experiment.

Research only; no production BEAN database or runtime modified.
Run: python -m unittest -v research/test_correction_receipt_replay.py
The canonical events table stores both facts and correction receipts.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


def setup(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, data TEXT, superseded_by INTEGER)")
    db.commit()
    return db


def correction(db, old, new):
    if type(old) is not int or type(new) is not int or old < 1 or new <= old:
        raise ValueError("correction must point to a later positive event")
    with db:
        changed = db.execute(
            "UPDATE events SET superseded_by=? WHERE id=? AND superseded_by IS NULL "
            "AND EXISTS (SELECT 1 FROM events WHERE id=?)", (new, old, new)
        ).rowcount
        if changed != 1:
            raise ValueError("missing or already corrected event")
        db.execute(
            "INSERT INTO events(event_type,data) VALUES (?,?)",
            ("world_model_update", json.dumps({
                "kind": "correction_receipt_v1", "original": old,
                "replacement": new}, sort_keys=True)),
        )


def replay(db):
    """Read-only comparison: never silently repair missing evidence."""
    receipts = []
    for (raw,) in db.execute(
        "SELECT data FROM events WHERE event_type='world_model_update' ORDER BY id"
    ):
        payload = json.loads(raw)
        if payload.get("kind") == "correction_receipt_v1":
            receipts.append((payload["original"], payload["replacement"]))
    links = list(db.execute(
        "SELECT id,superseded_by FROM events WHERE superseded_by IS NOT NULL ORDER BY id"
    ))
    return receipts, links, sorted(set(links).symmetric_difference(set(receipts)))


class CorrectionReplay(unittest.TestCase):
    def test_restart_reconstructs_exact_correction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.db"
            db = setup(path)
            db.executemany("INSERT INTO events(event_type) VALUES (?)",
                           [("observation",), ("fact_learned",)])
            db.commit()
            correction(db, 1, 2)
            db.close()
            db = setup(path)
            self.assertEqual(replay(db), ([(1, 2)], [(1, 2)], []))
            db.close()

    def test_failed_duplicate_leaves_single_receipt(self):
        db = setup(":memory:")
        db.executemany("INSERT INTO events(event_type) VALUES (?)",
                       [("observation",), ("fact_learned",), ("fact_learned",)])
        db.commit()
        correction(db, 1, 2)
        with self.assertRaises(ValueError):
            correction(db, 1, 3)
        self.assertEqual(replay(db), ([(1, 2)], [(1, 2)], []))

    def test_missing_receipt_is_detected_not_fabricated(self):
        db = setup(":memory:")
        db.executemany("INSERT INTO events(event_type) VALUES (?)",
                       [("observation",), ("fact_learned",)])
        db.execute("UPDATE events SET superseded_by=2 WHERE id=1")
        db.commit()
        self.assertEqual(replay(db), ([], [(1, 2)], [(1, 2)]))

    def test_invalid_target_does_not_append(self):
        db = setup(":memory:")
        db.execute("INSERT INTO events(event_type) VALUES ('observation')")
        db.commit()
        with self.assertRaises(ValueError):
            correction(db, 1, 99)
        self.assertEqual(replay(db), ([], [], []))


if __name__ == "__main__":
    unittest.main()

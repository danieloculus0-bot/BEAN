"""Synthetic integration checks for canonical event inventory authentication."""
import tempfile
import unittest
from pathlib import Path

from bean.memory.store import init_store
from bean.memory.event_logger import log_event, EventType
from bean.tests.analogy_canonical_event_control import (
    canonical_event_fingerprint, authenticate_candidate_inventory,
)


class CanonicalEventInventoryControl(unittest.TestCase):
    def test_real_event_survives_restart_and_forgery_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "bean.sqlite")
            store = init_store(db)
            event_id = log_event(
                "synthetic-session", EventType.OBSERVATION,
                "fictional test observation", data={"outcome": "unknown"},
            )
            row = store.fetchone(
                "SELECT event_uuid FROM events WHERE id = ?", (event_id,)
            )
            event_uuid = row["event_uuid"]
            fingerprint = canonical_event_fingerprint(store, event_uuid)
            self.assertTrue(fingerprint.startswith("bean-event-v1:"))
            inventory = {"case": {event_uuid: fingerprint}}
            self.assertEqual(
                authenticate_candidate_inventory(store, inventory), inventory
            )
            # Restart reopens the existing canonical database and mirror.
            reopened = init_store(db)
            self.assertEqual(
                canonical_event_fingerprint(reopened, event_uuid), fingerprint
            )
            with self.assertRaisesRegex(ValueError, "unverified canonical"):
                authenticate_candidate_inventory(
                    reopened, {"case": {"invented-receipt": fingerprint}}
                )
            with self.assertRaisesRegex(ValueError, "unverified canonical"):
                authenticate_candidate_inventory(
                    reopened, {"case": {event_uuid: "bean-event-v1:" + "0" * 64}}
                )
            # Source content changes invalidate the previous fingerprint.
            # This mutation is a deliberate test-only corruption, not a
            # supported production update to the append-only event history.
            reopened.execute(
                "UPDATE events SET summary = ? WHERE event_uuid = ?",
                ("tampered synthetic observation", event_uuid),
            )
            reopened.commit()
            with self.assertRaisesRegex(ValueError, "unverified canonical"):
                authenticate_candidate_inventory(reopened, inventory)


if __name__ == "__main__":
    unittest.main()

"""Independent synthetic tests for private pre-match training and camera protocol."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from .onboarding import LocalOnboarding, VIEWS

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.ledger = LocalOnboarding(START)
        self.ledger.begin()

    def populate(self):
        sessions = [
            (0, ("communication", "values")),
            (1, ("conflict", "lifestyle")),
            (4, ("attraction", "boundaries")),
            (6, ("friendship", "ambitions")),
        ]
        for i, (day, topics) in enumerate(sessions):
            self.ledger.record_session("session_" + str(i), START + timedelta(days=day),
                                       mode="voice" if i == 1 else "text",
                                       topics=topics, turn_count=8,
                                       duration_seconds=420)
        for angle in VIEWS:
            self.ledger.record_photo(angle, ("a" if angle == "front" else
                                              "b" if angle == "left" else "c") * 64,
                                     .88, owner_approved=True)

    def test_requires_seven_days_even_when_everything_else_complete(self):
        self.populate()
        s = self.ledger.status(START + timedelta(days=6, hours=10))
        self.assertFalse(s["matching_enabled"])
        self.assertIn("evaluation_period_incomplete", s["missing"])

    def test_full_training_and_final_person_consent(self):
        self.populate()
        check_at = START + timedelta(days=7)
        s = self.ledger.status(check_at)
        self.assertTrue(s["eligible_for_human_review"])
        self.assertFalse(s["matching_enabled"])
        self.assertEqual(s["voice_sessions"], 1)
        self.ledger.confirm_ready(check_at)
        self.assertTrue(self.ledger.public_gate(check_at)["matching_enabled"])
        self.assertEqual(set(self.ledger.public_gate(check_at)),
                         {"schema", "matching_enabled"})

    def test_no_raw_profile_secrets_emails_or_photos_in_export_gate(self):
        self.populate()
        self.ledger.confirm_ready(START + timedelta(days=7))
        gate = str(self.ledger.public_gate(START + timedelta(days=7)))
        for forbidden in ("sessions", "photos", "private_history", "photo",
                          "health", "email", "voice", "topics"):
            self.assertNotIn(forbidden, gate)

    def test_incomplete_photo_blocks_and_retake_requires_review(self):
        self.populate()
        self.ledger.record_photo("left", "e" * 64, .25, owner_approved=True)
        s = self.ledger.status(START + timedelta(days=8))
        self.assertIn("guided_photo_capture_incomplete", s["missing"])
        self.ledger.record_photo("left", "d" * 64, .95, owner_approved=True)
        self.assertTrue(self.ledger.status(START + timedelta(days=8))["eligible_for_human_review"])
        self.ledger.confirm_ready(START + timedelta(days=8))
        self.ledger.record_photo("front", "a" * 64, .9, owner_approved=False)
        self.assertFalse(self.ledger.status(START + timedelta(days=8))["matching_enabled"])

    def test_requires_multiple_days_and_meaningful_turns(self):
        for i in range(6):
            self.ledger.record_session("talk_%d" % i, START + timedelta(hours=i),
                                       mode="text", topics=["communication", "values"],
                                       turn_count=1 if i == 0 else 8,
                                       duration_seconds=30 if i == 0 else 220)
        s = self.ledger.status(START + timedelta(days=8))
        self.assertIn("insufficient_distinct_days", s["missing"])
        self.assertIn("insufficient_topic_coverage", s["missing"])

    def test_consent_and_replay(self):
        x = LocalOnboarding(START)
        with self.assertRaises(PermissionError):
            x.record_session("session_x", START, mode="text",
                             topics=["values"], turn_count=5, duration_seconds=180)
        self.assertTrue(self.ledger.record_session("session_1", START,
                        mode="text", topics=["values"], turn_count=5, duration_seconds=180))
        self.assertFalse(self.ledger.record_session("session_1", START,
                         mode="text", topics=["values"], turn_count=5, duration_seconds=180))
        with self.assertRaises(ValueError):
            self.ledger.record_session("session_1", START,
                                       mode="text", topics=["values"], turn_count=6,
                                       duration_seconds=180)

    def test_invalid_dates_and_photo_evidence_rejected(self):
        with self.assertRaises(ValueError):
            LocalOnboarding("2026-01-01")
        with self.assertRaises(ValueError):
            self.ledger.record_session("session_invalid", START - timedelta(days=1),
                                       mode="text", topics=["values"], turn_count=8,
                                       duration_seconds=350)
        with self.assertRaises(ValueError):
            self.ledger.record_photo("back", "a"*64, .8, owner_approved=True)
        with self.assertRaises(ValueError):
            self.ledger.record_photo("front", "raw-user-photo", .8,
                                     owner_approved=True)
        with self.assertRaises(ValueError):
            self.ledger.record_photo("front", "a"*64, 5, owner_approved=True)

    def test_guided_browser_camera_capture_source_contract(self):
        text = (Path(__file__).with_name("camera_onboarding.html")
                .read_text(encoding="utf-8"))
        self.assertIn("getUserMedia", text)
        self.assertIn("speechSynthesis", text)
        self.assertIn("front", text)
        self.assertIn("left", text)
        self.assertIn("right", text)
        self.assertIn("crypto.subtle.digest", text)
        self.assertNotIn("fetch(", text)
        self.assertNotIn("localStorage", text)


if __name__ == "__main__":
    unittest.main()

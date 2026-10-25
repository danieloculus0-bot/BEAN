"""The actual CommandInbox must accept bounded atomic requests without logging sensitive payloads."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bean.runtime.inbox import CommandInbox, MAX_INBOX_BYTES


class InboxRequestHandlingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.inbox = CommandInbox(Path(self.temp.name) / "inbox")

    def test_atomically_publish_one_request_and_keep_secrets_out_of_event_log(self):
        seen = []
        self.inbox.register("reasoning_reason",
                            lambda msg, session: seen.append(msg.args) or
                            {"answer": "CONFIDENTIAL-ANSWER", "ok": True})
        args = {"prompt": "CUSTOMER_CONFIDENTIAL_TEXT",
                "api_key": "TEST_SECRET_STRING"}
        p = self.inbox.drop("reasoning_reason", args=args)
        self.assertTrue(p.is_file())
        self.assertEqual(list(self.inbox.inbox_dir.glob("*.tmp")), [])
        events = []
        with patch("bean.runtime.inbox.log_event", side_effect=lambda *a, **kw: events.append((a, kw))):
            out = self.inbox.poll("test-session")
        self.assertEqual(out[0]["status"], "ok")
        self.assertEqual(seen, [args])
        self.assertFalse(p.exists())
        recorded = json.dumps(events)
        self.assertNotIn("CUSTOMER_CONFIDENTIAL_TEXT", recorded)
        self.assertNotIn("TEST_SECRET_STRING", recorded)
        self.assertNotIn("CONFIDENTIAL-ANSWER", recorded)
        self.assertIn("reasoning_reason", recorded)

    def test_oversized_input_is_rejected_before_queueing(self):
        with self.assertRaisesRegex(ValueError, "maximum|bounded|size"):
            self.inbox.drop("reasoning_reason", {"prompt": "x" * MAX_INBOX_BYTES})
        self.assertEqual(list(self.inbox.inbox_dir.glob("*.json")), [])

    def test_external_bad_requests_are_quarantined_not_run(self):
        called = []
        self.inbox.register("reasoning_reason", lambda msg, session: called.append(1))
        oversized = self.inbox.inbox_dir / "too-large.json"
        oversized.write_text(" " * (MAX_INBOX_BYTES + 1))
        wrong_type = self.inbox.inbox_dir / "wrong-type.json"
        wrong_type.write_text(json.dumps({"command": "reasoning_reason", "args": ["not a dict"]}))
        malformed = self.inbox.inbox_dir / "partial.json"
        malformed.write_text('{"command":"reasoning_reason",')
        with patch("bean.runtime.inbox.log_event"):
            results = self.inbox.poll("test-session")
        self.assertEqual(len(results), 3)
        self.assertEqual(sorted(x["status"] for x in results),
                         ["invalid_args", "parse_error", "parse_error"])
        self.assertFalse(called)
        self.assertEqual(len(list(self.inbox.failed_dir.glob("*.json"))), 3)


if __name__ == "__main__":
    unittest.main()

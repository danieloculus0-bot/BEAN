"""Real BEAN CommandInbox integration for idealized spaceflight references.

The actual inbox queue, registration and dispatch are exercised. The canonical
SQLite event writer is patched to inspect the exact audit payload without
creating a production database or exposing a caller's request in test logs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bean.engineering.spaceflight import REQUEST_SCHEMA, solve_spaceflight_reference
from bean.memory.event_logger import EventType, Source
from bean.runtime.inbox import CommandInbox
from bean.runtime.inbox_handlers import make_handlers, register_all


def digest(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SpaceflightInboxTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.inbox = register_all(CommandInbox(Path(tmp.name) / "inbox"))

    def test_registered_in_actual_runtime_handler_map(self):
        self.assertIn("spaceflight_reference", make_handlers())
        self.assertIn("spaceflight_reference", self.inbox._handlers)

    def test_mars_reference_uses_existing_solver_and_records_only_hashes(self):
        request = {
            "schema": REQUEST_SCHEMA, "calculation": "mars_transfer",
            "parameters": {}, "source_ref": "PRIVATE-NOTE-NOT-FOR-LEDGER",
        }
        expected = solve_spaceflight_reference(request)
        self.inbox.drop("spaceflight_reference", args=request)
        with (patch("bean.runtime.inbox.log_event") as inbox_log,
              patch("bean.runtime.inbox_handlers.log_event", return_value=73) as physics_log):
            out = self.inbox.poll("test-session")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["status"], "ok")
        self.assertEqual(out[0]["result"]["schema"], expected["schema"])
        self.assertEqual(out[0]["result"]["result"], expected["result"])
        receipt = out[0]["result"]["evidence_receipt"]
        self.assertEqual(receipt["event_id"], 73)
        self.assertEqual(receipt["request_sha256"], digest(request))
        self.assertEqual(receipt["result_sha256"], digest(expected))
        self.assertFalse(out[0]["result"]["flight_qualified"])
        self.assertFalse(out[0]["result"]["independently_validated"])
        self.assertEqual(physics_log.call_count, 1)
        args, kwargs = physics_log.call_args
        self.assertEqual(args[0], "test-session")
        self.assertEqual(args[1], EventType.OBSERVATION)
        self.assertEqual(args[3], Source.SYSTEM)
        self.assertEqual(kwargs["subtype"], "spaceflight_idealized_reference")
        self.assertEqual(kwargs["data"]["request_sha256"], digest(request))
        self.assertEqual(kwargs["data"]["result_sha256"], digest(expected))
        self.assertFalse(kwargs["data"]["source_authenticated"])
        self.assertFalse(kwargs["data"]["learning_weights_updated"])
        # Neither the ordinary inbox event nor the extra observation may
        # publish the raw request or the supplied reference string.
        logged = repr(inbox_log.call_args_list) + repr(physics_log.call_args_list)
        self.assertNotIn("PRIVATE-NOTE-NOT-FOR-LEDGER", logged)
        self.assertNotIn("1.523679", logged)

    def test_two_body_command_executes_actual_numeric_solver(self):
        request = {
            "schema": REQUEST_SCHEMA, "calculation": "two_body_propagation",
            "parameters": {
                "body": "earth", "position_km": [7000, 0, 0],
                "velocity_km_s": [0, 7.5, 0],
                "step_seconds": 5, "steps": 10,
            },
        }
        self.inbox.drop("spaceflight_reference", args=request)
        with (patch("bean.runtime.inbox.log_event"),
              patch("bean.runtime.inbox_handlers.log_event", return_value=74)):
            result = self.inbox.poll("test-session")[0]
        self.assertEqual(result["status"], "ok")
        reference = result["result"]
        self.assertEqual(reference["result"]["steps"], 10)
        self.assertEqual(reference["result"]["body"], "earth")
        self.assertLess(reference["result"]["max_scaled_specific_energy_drift"], 1e-4)
        self.assertFalse(reference["flight_qualified"])

    def test_invalid_input_fails_closed_without_observation(self):
        bad = {
            "schema": REQUEST_SCHEMA, "calculation": "orbit",
            "parameters": {"body": "mars", "altitude_km": -10},
        }
        self.inbox.drop("spaceflight_reference", args=bad)
        with (patch("bean.runtime.inbox.log_event") as inbox_log,
              patch("bean.runtime.inbox_handlers.log_event") as physics_log):
            out = self.inbox.poll("test-session")
        self.assertEqual(out[0]["status"], "handler_error")
        self.assertEqual(out[0]["exception_class"], "ValueError")
        physics_log.assert_not_called()
        self.assertTrue(any(x.kwargs.get("subtype") == "inbox_handler_error"
                            for x in inbox_log.call_args_list))
        self.assertEqual(len(list(self.inbox.failed_dir.glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()

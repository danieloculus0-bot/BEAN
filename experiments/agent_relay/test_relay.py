"""Independent offline acceptance tests for the experimental agent-to-agent bridge."""
from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError

from .agent import local_preference_review, model_signal
from .client import AgentClient
from .demo import TOKENS, run_demo
from .protocol import message, validate_message
from .relay import Relay, make_server


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.relay = Relay(TOKENS)
        self.server = make_server(self.relay)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        addr = "http://127.0.0.1:" + str(self.server.server_port)
        self.a = AgentClient(addr, TOKENS["agentA"])
        self.b = AgentClient(addr, TOKENS["agentB"])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def envelope(self, message_id="m01"):
        return message(message_id=message_id, session_id="s01", sender="agentA",
                       recipient="agentB", kind="probe", topic="hobbies",
                       detail="creative_making", signal="interested")

    def test_two_real_http_agents_exchange_without_profiles(self):
        self.assertTrue(self.a.send(self.envelope())["accepted"])
        self.assertEqual(self.b.inbox(), [self.envelope()])
        self.assertEqual(self.b.inbox(), [])

    def test_sender_ownership_and_no_cross_inbox(self):
        with self.assertRaises(HTTPError) as fail:
            self.b.send(self.envelope())
        self.assertEqual(fail.exception.code, 403)
        self.assertEqual(self.a.inbox(), [])
        self.assertEqual(self.b.inbox(), [])

    def test_missing_or_wrong_token_fails(self):
        with self.assertRaises(ValueError):
            AgentClient("http://not-local:9000", TOKENS["agentA"])
        with self.assertRaises(HTTPError) as fail:
            AgentClient(self.a.base_url, "a-very-long-but-incorrect-token-000").inbox()
        self.assertEqual(fail.exception.code, 401)

    def test_repeat_idempotent_and_conflicting_replay(self):
        self.assertTrue(self.a.send(self.envelope())["accepted"])
        self.assertTrue(self.a.send(self.envelope())["duplicate"])
        self.assertEqual(len(self.b.inbox()), 1)
        altered = self.envelope()
        altered["signal"] = "incompatible"
        with self.assertRaises(HTTPError) as fail:
            self.a.send(altered)
        self.assertEqual(fail.exception.code, 400)

    def test_private_fields_raw_text_and_unknown_topics_rejected(self):
        for field, value in (("private_history", "a secret"), ("email", "a@example.org"),
                             ("medical_history", "private"), ("free_text", "hi")):
            altered = self.envelope()
            altered[field] = value
            with self.assertRaises(ValueError):
                validate_message(altered)
        altered = self.envelope()
        altered["detail"] = "john smith works at a factory"
        with self.assertRaises(ValueError):
            validate_message(altered)
        altered = self.envelope()
        altered["topic"] = "medical"
        with self.assertRaises(ValueError):
            validate_message(altered)

    def test_backpressure_and_failed_send_preserves_inbox(self):
        relay = Relay(TOKENS, queue_limit=1)
        self.assertTrue(relay.deliver("agentA", self.envelope())["accepted"])
        with self.assertRaises(ValueError):
            relay.deliver("agentA", self.envelope("m02"))
        self.assertEqual(relay.receive("agentB"), [self.envelope()])

    def test_private_flexibility_question_never_exits_agent(self):
        result = local_preference_review(requested_minimum=160,
                                         candidate_value=150, flexible=True)
        self.assertEqual(result["decision"], "ask_local")
        self.assertTrue(result["needs_user_decision"])
        self.assertEqual(result["gap"], 10)
        result2 = local_preference_review(requested_minimum=160,
                                          candidate_value=150, flexible=False)
        self.assertEqual(result2["decision"], "declined")
        self.assertFalse(result2["needs_user_decision"])
        self.assertNotIn("requested_minimum", json.dumps(self.envelope()))

    def test_model_connector_fails_without_real_response_and_rejects_extra_fields(self):
        class Available:
            def complete(self, prompt):
                self.prompt = prompt
                return {"ok": True, "raw_text": '{"signal":"interested"}'}
        class Leaky:
            def complete(self, prompt):
                return {"ok": True, "raw_text":
                        '{"signal":"interested","private_history":"secret"}'}
        class Down:
            def complete(self, prompt):
                return {"ok": False, "error": "offline"}
        self.assertEqual(model_signal(Available(), topic="hobbies",
                                      public_detail="creative_making"), "interested")
        with self.assertRaises(ValueError):
            model_signal(Leaky(), topic="hobbies", public_detail="creative_making")
        with self.assertRaises(RuntimeError):
            model_signal(Down(), topic="hobbies", public_detail="creative_making")

    def test_end_to_end_synthetic_demo(self):
        result = run_demo()
        self.assertEqual(result["delivered_messages"], 2)
        self.assertEqual(result["local_preference_review"], "ask_local")
        self.assertFalse(result["real_model_inference"])


if __name__ == "__main__":
    unittest.main()

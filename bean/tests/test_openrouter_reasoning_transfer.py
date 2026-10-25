"""Offline OpenRouter adapter checks; never counted as real-model evidence."""
import json
import unittest
from bean.evaluation.live_reasoning_transfer import DEVELOPMENT
from bean.evaluation.openrouter_reasoning_transfer import (
    OpenRouterFreeReasoner, MODEL, ENDPOINT,
)


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self, n):
        return json.dumps({
            "id": "free_test_response",
            "model": MODEL,
            "choices": [{"message": {"content": "UNKNOWN"}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 12},
        }).encode()


class OpenRouterReasoningAdapterTests(unittest.TestCase):
    def test_only_free_pinned_model_and_public_question_are_sent(self):
        seen = []

        def fake_call(req, timeout):
            payload = json.loads(req.data.decode())
            self.assertEqual(req.full_url, ENDPOINT)
            self.assertEqual(payload["model"], MODEL)
            self.assertTrue(payload["model"].endswith(":free"))
            self.assertEqual(timeout, 90)
            self.assertNotIn(DEVELOPMENT.expected, req.data.decode())
            self.assertNotIn("unit-key", req.data.decode())
            seen.append(payload)
            return Response()

        model = OpenRouterFreeReasoner(
            "unit-key", model=MODEL, request_fn=fake_call)
        self.assertEqual(model.complete(DEVELOPMENT.public_question, ""), "UNKNOWN")
        self.assertEqual(model.calls[0]["model_served"], MODEL)
        self.assertEqual(len(seen), 1)
        self.assertNotIn("tools", seen[0])
        self.assertNotIn("temperature", seen[0])


if __name__ == "__main__":
    unittest.main()

"""Offline contracts for the real-provider research runner; NOT live evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bean.evaluation.live_reasoning_transfer import (
    DEVELOPMENT, RULE, HOLDOUT, LiveProviderError, OpenAIReasoningModel,
    run, verdict,
)


class RecordedFixture:
    provider_kind = "real_model"
    model_id = "fixture-not-a-real-reasoner"

    def __init__(self, key, model):
        self.calls = []
        self.model_id = model

    def complete(self, question, context):
        import re
        tokens = re.findall(r"\b([A-Z])([0-9])\b", question)
        answer = ("".join(letter for letter, number in sorted(
            tokens, key=lambda item: int(item[1]))) if RULE in context
                  or "ASTER-7 dispatch key procedure" in context
                  else "UNKNOWN")
        self.calls.append({
            "model_served": "mock-provider",
            "response_id": "fixture" + str(len(self.calls)),
            "answer": answer,
        })
        return answer


class Response:
    def __init__(self, doc):
        self.doc = doc

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self, limit):
        return json.dumps(self.doc).encode()


class RealReasoningResearchTests(unittest.TestCase):
    def test_absent_credential_is_reported_not_fake_success(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run(Path(temp) / "first", key="")
            self.assertEqual(result["status"], "blocked_no_api_key")
            self.assertEqual(result["requests"], 0)
            saved = json.loads((Path(temp) / "first" / "report.json").read_text())
            self.assertEqual(saved["status"], "blocked_no_api_key")

    def test_real_api_request_shape_does_not_send_expected_answers(self):
        captured = []

        def request(request, timeout=90):
            raw = request.data.decode()
            payload = json.loads(raw)
            captured.append(payload)
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertEqual(payload["model"], "gpt-6.1-sol")
            self.assertEqual(payload["reasoning"], {"effort": "medium"})
            self.assertNotIn("temperature", payload)
            self.assertNotIn("CYN", raw)
            self.assertNotIn("Authorization", raw)
            return Response({
                "id": "resp_fixture_1",
                "model": "gpt-6.1-sol",
                "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "UNKNOWN"}]}],
                "usage": {"input_tokens": 25, "output_tokens": 2,
                          "total_tokens": 27},
            })

        provider = OpenAIReasoningModel(
            "unit-test-token", request_fn=request)
        reply = provider.complete(DEVELOPMENT.public_question, "")
        self.assertEqual(reply, "UNKNOWN")
        self.assertEqual(provider.calls[0]["model_served"], "gpt-6.1-sol")
        self.assertEqual(len(captured), 1)

    def test_experimental_fake_only_proves_infrastructure(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "fixture"
            result = run(output, key="fixture-key", model_factory=RecordedFixture)
            self.assertEqual(result["selection"]["arm"], "reflection")
            self.assertEqual(result["holdout_trial"]["scores"],
                             {"cold": 0, "placebo": 0, "adaptive": 2})
            self.assertTrue(result["restart_selection_identical"])
            self.assertEqual(result["holdout_increment_over_cold"], 2)
            self.assertFalse(result["independent_blindness_authenticated"])
            self.assertFalse(result["weight_learning"])
            self.assertTrue((output / "experience.sqlite3").exists())
            self.assertEqual(result["requests"], 18)
            self.assertEqual(len(result["model_calls"]), 18)

    def test_refuses_to_rewrite_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "study"
            run(output, key="fixture-key", model_factory=RecordedFixture)
            with self.assertRaises(FileExistsError):
                run(output, key="fixture-key", model_factory=RecordedFixture)

    def test_heldout_answers_are_disjoint(self):
        self.assertNotIn(DEVELOPMENT.public_question,
                         [case.public_question for case in HOLDOUT])
        self.assertTrue(all(not verdict(case.expected, "UNKNOWN")
                            for case in HOLDOUT))


if __name__ == "__main__":
    unittest.main()

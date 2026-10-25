"""Offline safety/structural tests; synthetic fixtures DO NOT count as live learning."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from bean.evaluation.nemotron_self_derived_transfer import (
    DOMAINS, MAX_CALLS, MODEL, RecordingNemotron, run, task_fingerprints
)
from bean.evaluation.live_reasoning_transfer import LiveProviderError


class SimulatedModel:
    provider_kind = "synthetic_fixture"
    """Controlled fixture, NEVER passed off as a real external reasoning model."""
    def __init__(self, key, *, model, output):
        self.model_id = model
        self.calls = []
        self.output = Path(output)

    def _answer(self, question, context):
        if "ORCHID-7" in question:
            if not ("highest digit" in context or
                    "Training examples only: ORCHID-7" in context):
                return "UNKNOWN"
            tokens = re.findall(r"\b([A-Z])([0-9])\b", question)
            return "".join(k for k, v in sorted(
                tokens, key=lambda x: int(x[1]), reverse=True))
        if "HARBOR-4" in question:
            if not ("middle of the three" in context or
                    "Training examples only: HARBOR-4" in context):
                return "UNKNOWN"
            tokens = re.findall(r"\b([A-Z])=(\d+)\b", question)
            return sorted(tokens, key=lambda x: int(x[1]))[1][0]
        return "UNKNOWN"

    def complete(self, question, context):
        if len(self.calls) >= MAX_CALLS:
            raise LiveProviderError("Fake exceeded budget")
        ans = self._answer(question, context)
        self.calls.append({
            "model_served": MODEL, "kind": "synthetic_fixture",
            "answer": ans, "response_id": str(len(self.calls)),
        })
        return ans

    def complete_batch(self, items):
        if len(self.calls) >= MAX_CALLS:
            raise LiveProviderError("Fixture batch budget exceeded")
        if len({x["task_id"] for x in items}) != len(items):
            raise ValueError("Duplicate task identity in batch")
        answers = {
            x["task_id"]: self._answer(x["question"], x["context"])
            for x in items
        }
        self.calls.append({
            "model_served": MODEL,
            "kind": "synthetic_fixture_batch",
            "answers": answers, "response_id": str(len(self.calls)),
        })
        return answers

    def infer_rule(self, domain, examples):
        if "orchid" in domain:
            rule = "For ORCHID-7 order tag letters from highest digit to lowest."
        else:
            rule = "For HARBOR-4 choose the label with the middle of the three readings."
        self.calls.append({
            "model_served": MODEL, "kind": "synthetic_fixture",
            "answer": rule, "response_id": str(len(self.calls)),
        })
        return rule, str(len(self.calls))


class FixtureResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self): return self
    def __exit__(self, *unused): return False
    def read(self, limit): return json.dumps(self.data).encode()


class ModelAuthoredReasoningTests(unittest.TestCase):
    def test_two_diverse_disjoint_rule_families(self):
        questions = task_fingerprints()
        self.assertEqual(len(DOMAINS), 2)
        self.assertEqual(len(questions), 20)
        self.assertEqual(len({q.task_id for q in questions}), len(questions))
        self.assertTrue(all(len(d.holdout) == 4 for d in DOMAINS))
        self.assertNotEqual(DOMAINS[0].name, DOMAINS[1].name)

    def test_no_secret_marks_a_block_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            r = run(Path(temp)/"no_key", api_key="")
            self.assertEqual(r["status"], "blocked_no_api_key")
            self.assertEqual(r["requests"], 0)
            self.assertFalse((Path(temp)/"no_key"/"experience.sqlite3").exists())

    def test_synthetic_mock_only_contract_scoring_and_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            r = run(Path(temp)/"fixture", api_key="unit-test",
                    model_factory=SimulatedModel)
            self.assertEqual(r["status"], "completed_all_families")
            self.assertEqual(r["requests"], 22)  # 11 isolated calls x 2 domains
            self.assertEqual(len(r["domains"]), 2)
            for d in r["domains"]:
                self.assertEqual(d["status"], "evaluated_with_synthetic_fixture")
                self.assertTrue(d["validation"]["passed"])
                self.assertEqual(d["selection"]["trial"]["scores"]["cold"], 0)
                self.assertEqual(d["selection"]["trial"]["scores"]["placebo"], 0)
                self.assertEqual(d["holdout"]["trial"]["scores"]["cold"], 0)
                self.assertEqual(d["holdout"]["trial"]["scores"]["placebo"], 0)
                self.assertEqual(d["holdout"]["trial"]["scores"]["adaptive"], 4)
                self.assertEqual(d["holdout"]["trial"]["batching_policy"],
                                 "one_isolated_request_per_arm_v1")
                self.assertEqual(d["holdout"]["trial"]["provider_requests"], 3)
                self.assertEqual(d["selection"]["trial"]["provider_requests"], 5)
                self.assertEqual(d["selected_strategy"], "reflection")
                self.assertEqual(d["restored_decision"]["selected_strategy"],
                                 "reflection")
            self.assertEqual(r["source"], "evaluator_authored_fictional_protocols")
            self.assertFalse(r["independent_blindness_authenticated"])
            self.assertFalse(r["model_weights_changed"])
            self.assertTrue((Path(temp)/"fixture"/"experience.sqlite3").is_file())
            self.assertFalse((Path(temp)/"fixture"/"provider_calls.jsonl").exists())
            # The synthetic fixture is only a unit test; it never produces
            # the real provider_calls.jsonl proving actual remote responses.

    def test_reflection_request_is_derived_from_only_development_examples(self):
        seen = []
        def fake_send(req, timeout=90):
            payload = json.loads(req.data.decode())
            self.assertEqual(payload["model"], MODEL)
            self.assertTrue(payload["model"].endswith(":free"))
            s = json.dumps(payload)
            self.assertNotIn("orchid-holdout", s)
            for c in DOMAINS[0].holdout:
                self.assertNotIn(c.public_question, s)
                self.assertNotIn(c.expected + "XYZ_NOT_VALID", s)
            for c in DOMAINS[0].demonstrations:
                self.assertIn(c.public_question, s)
                self.assertIn(c.expected, s)
            seen.append(payload)
            return FixtureResponse({
                "id": "model-rule-response", "model": MODEL,
                "choices": [{"message": {"content":
                    "For ORCHID-7 sort tags by descending numeric digit, "
                    "joining letters."}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 20},
            })
        with tempfile.TemporaryDirectory() as temp:
            provider=RecordingNemotron("fixture-key", output=Path(temp),
                                       request_fn=fake_send)
            lesson, rid = provider.infer_rule(
                DOMAINS[0].name, DOMAINS[0].demonstrations)
            self.assertIn("descending numeric digit", lesson)
            self.assertEqual(rid, "model-rule-response")
            self.assertEqual(len(seen), 1)
            saved = (Path(temp)/"provider_calls.jsonl").read_text().splitlines()
            self.assertEqual(len(saved), 1)
            self.assertEqual(json.loads(saved[0])["kind"], "model_authored_rule")

    def test_verbose_real_answer_is_recorded_and_scored_wrong(self):
        from bean.evaluation.nemotron_self_derived_transfer import correct
        expected = "PDK"
        verbose = "I cannot confirm that ORCHID-7 has any meaningful rule. " * 16

        def fake_send(req, timeout=90):
            return FixtureResponse({
                "id": "long-actual-reply", "model": MODEL,
                "choices": [{"message": {"content": verbose}}],
                "usage": {"prompt_tokens": 30, "completion_tokens": 190},
            })

        with tempfile.TemporaryDirectory() as temp:
            provider = RecordingNemotron(
                "unit-test", output=Path(temp), request_fn=fake_send)
            response = provider.complete(
                DOMAINS[0].demonstrations[0].public_question, "")
            self.assertGreater(len(response), 300)
            self.assertEqual(response, verbose.strip())
            self.assertFalse(correct(expected, response))
            log = (Path(temp) / "provider_calls.jsonl").read_text().splitlines()
            self.assertEqual(len(log), 1)
            self.assertEqual(json.loads(log[0])["answer"], response)
            self.assertEqual(json.loads(log[0])["kind"], "scored_task")

    def test_budget_cap_and_no_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"archive"
            run(p, api_key="unit-test", model_factory=SimulatedModel)
            with self.assertRaises(FileExistsError):
                run(p, api_key="unit-test", model_factory=SimulatedModel)


if __name__ == "__main__":
    unittest.main()

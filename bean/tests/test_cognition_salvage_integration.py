"""Regression coverage for earlier unmerged working cognitive mechanisms.

These checks exercise ordinary BEAN Core storage rather than asserting a
general intelligence advantage or requiring a real external model.
"""
import json
import tempfile
import unittest
from pathlib import Path

from bean.reasoning.prompt_builder import build_ollama_prompt


class CognitionSalvageTests(unittest.TestCase):
    def test_reasoning_context_preserves_older_measured_failure_and_values(self):
        events = [
            {"id": 9, "summary": "latest", "data": '{"x":1}', "source": "system"},
            {"id": 8, "summary": "new", "data": "{}", "source": "system"},
            {"id": 7, "summary": "recent", "data": "{}", "source": "system"},
            {"id": 6, "summary": "unrelated", "data": "{}", "source": "system"},
            {"id": 5, "summary": "actual experiment failure",
             "subtype": "cognitive_module_failure",
             "data": '{"trial":"trial-55","reward":-0.7}', "source": "system"},
        ]
        generated = build_ollama_prompt({"recent_events": events})
        packet = json.loads(generated.split("EVIDENCE:\n", 1)[1])
        ids = [x["id"] for x in packet["recent_events"]]
        self.assertIn(5, ids)
        item = next(x for x in packet["recent_events"] if x["id"] == 5)
        self.assertEqual(item["data"]["reward"], -0.7)
        self.assertEqual(item["data"]["trial"], "trial-55")
        self.assertEqual(packet["recent_events"][0]["data"]["x"], 1)

    def test_repeated_goal_does_not_spawn_duplicates_and_test_goal_is_native(self):
        from bean.runtime.bootstrap import start_bean, shutdown_bean
        from bean.cognition.goal_state import GoalStateEngine, ActionType
        with tempfile.TemporaryDirectory() as root:
            ctx = start_bean(db_path=str(Path(root) / "bean.db"), silent=True)
            try:
                engine = GoalStateEngine()
                questions = [
                    {"id": 77, "question": "Which method predicts an outcome?",
                     "context": json.dumps({
                         "schema": "bean.cognition.experiment.v1",
                         "capability": "prediction", "inputs": {"x": 4},
                         "expected_output": {"y": 9}})},
                    {"id": 78, "question": "What is this unknown?", "context": ""},
                ]
                new = engine.propose(ctx["session_uuid"], [], questions)
                self.assertEqual(len(new), 2)
                self.assertEqual(new[0].action_type, ActionType.RUN_EXPERIMENT)
                self.assertEqual(new[0].action_detail["question_id"], 77)
                self.assertTrue(all(x.status == "pending" for x in new))
                next_pass = engine.propose(ctx["session_uuid"], [], questions)
                self.assertEqual(next_pass, [])
                self.assertEqual(len(engine.get_pending(ctx["session_uuid"])), 2)
            finally:
                shutdown_bean(ctx)


if __name__ == "__main__":
    unittest.main()

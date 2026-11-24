"""Exercise the newly connected tools against the real persistent reasoning service."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bean.learning.reasoning_service import NativeReasoningService
from bean.runtime.retained_reasoning_tools import register_retained_reasoning


class RetainedReasoningAssimilationTests(unittest.TestCase):
    def test_native_discovery_and_replay_after_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reasoning.sqlite"
            core = NativeReasoningService(path)
            samples = {str(i): (i - 6, 1 if i % 2 else -1) for i in range(13)}
            def reward(pid, action):
                expected = (samples[pid][0] > 0) - (samples[pid][0] < 0)
                return float(action == expected)
            try:
                result = core.discover_analogy(
                    domain="fixture", task_ref="train", source_ref="synthetic:fixture",
                    probe_ids=list(samples), observe=samples.__getitem__,
                    reward=reward, budget=13)
                self.assertEqual(result["status"], "provisional_rule", result)
            finally:
                core.close()
            core = NativeReasoningService(path)
            try:
                tools = {}
                orchestrator = SimpleNamespace(
                    core=core, register=lambda name, description, handler:
                    tools.update({name: handler}))
                register_retained_reasoning(orchestrator)
                self.assertEqual(set(tools), {"reason_auto", "retained_strategy",
                    "discover_retained_policies", "apply_retained_policy"})
                found = tools["discover_retained_policies"]({"domain": "fixture"}, "find")
                self.assertEqual(found["count"], 1)
                item = found["policies"][0]
                self.assertEqual(item["receipt_id"], result["receipt_id"])
                args = {"kind": item["kind"], "receipt_id": item["receipt_id"],
                        "sensors": [17, -2]}
                replay = tools["apply_retained_policy"](args, "reuse")
                self.assertEqual(replay["action"], 1)
                args["sensors"] = [-19, 4]
                self.assertEqual(tools["apply_retained_policy"](args, "reuse2")["action"], -1)
                args["sensors"] = [1, 2, 3]
                with self.assertRaises(ValueError):
                    tools["apply_retained_policy"](args, "bad-layout")
                self.assertEqual(tools["discover_retained_policies"](
                    {"domain": "unrelated"}, "other")["count"], 0)
                choice = tools["retained_strategy"](
                    {"domain": "fixture", "query": "choose a policy"}, "strategy")
                self.assertIn("selected_strategy", choice)
            finally:
                core.close()


if __name__ == "__main__":
    unittest.main()

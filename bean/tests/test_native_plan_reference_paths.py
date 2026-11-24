"""Regression for model-generated scalar paths and recovery evidence keys."""
import unittest
import json
import io

from bean.reasoning.local_llamacpp_provider import LocalLlamaCppProvider
from bean.learning.reasoning_service import _model_response

from bean.runtime.native_orchestration import _path, _validate_known_reference_paths


class NativePlanReferencePathsTest(unittest.TestCase):
    def test_scalar_path_is_terminal(self):
        with self.assertRaisesRegex(ValueError, "scalar"):
            _validate_known_reference_paths(
                {"left": {"$step": 0, "path": ["prediction", 0]}},
                ["mean_sign"], {})
        _validate_known_reference_paths(
            {"left": {"$step": 0, "path": ["prediction"]}},
            ["mean_sign"], {})

    def test_recovery_uses_string_keys(self):
        inputs = {"__recovery": {"completed": {"0": {"mean": 4.0}}}}
        with self.assertRaisesRegex(ValueError, "object field"):
            _validate_known_reference_paths(
                {"left": {"$input": ["__recovery", "completed", 0, "mean"]}},
                [], inputs)
        _validate_known_reference_paths(
            {"left": {"$input": ["__recovery", "completed", "0", "mean"]}},
            [], inputs)

    def test_runtime_list_bounds_and_static_variable_length(self):
        _validate_known_reference_paths(
            {"$step": 0, "path": ["history", 4]}, ["numeric_context"], {})
        with self.assertRaisesRegex(ValueError, "list index"):
            _path({"history": [1, 2]}, ["history", 4])
        self.assertEqual(_path({"history": [1, 2]}, ["history", 1]), 2)

    def test_unknown_tool_paths_remain_runtime_resolved(self):
        _validate_known_reference_paths(
            {"$step": 0, "path": ["new_field", "nested"]},
            ["extension_tool"], {})


class StructuredPlannerProviderTest(unittest.TestCase):
    def test_json_mode_and_normal_chat_remain_distinct(self):
        requests = []
        def request(req, timeout):
            requests.append(json.loads(req.data))
            return io.BytesIO(json.dumps({
                "model": "qwen2.5:7b", "id": "test",
                "choices": [{"message": {"content": '{"steps":[]}'}}]
            }).encode())
        provider = LocalLlamaCppProvider(
            base_url="http://127.0.0.1:11434", model_name="qwen2.5:7b",
            requester=request)
        response = _model_response(provider, "Make a plan", "test", json_object=True)
        self.assertEqual(json.loads(response[0]), {"steps": []})
        self.assertEqual(requests[-1]["response_format"], {"type": "json_object"})
        self.assertEqual(requests[-1]["temperature"], 0)
        provider.complete("Hello")
        self.assertNotIn("response_format", requests[-1])

    def test_existing_generic_provider_compatibility(self):
        class Model:
            model_id = "test"
            provider_kind = "synthetic_fixture"
            def complete(self, prompt, context):
                return '{"steps":[]}'
        self.assertEqual(_model_response(Model(), "plan", None, json_object=True)[0],
                         '{"steps":[]}')


if __name__ == "__main__":
    unittest.main()

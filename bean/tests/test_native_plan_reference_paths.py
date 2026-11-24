"""Regression for model-generated scalar paths and recovery evidence keys."""
import unittest
import json
import io

from bean.reasoning.local_llamacpp_provider import LocalLlamaCppProvider
from bean.learning.reasoning_service import _model_response

from bean.runtime.native_orchestration import _path, _validate_known_reference_paths, _validate_numeric_tool_args


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


class NumericArgumentShapeTest(unittest.TestCase):
    def test_rejects_reference_tokens_and_object_wrappers(self):
        for malformed in (["$step", 0, "history"], {"ref": {"$step": 0, "path": ["history"]}}, {"$step": 0}):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(ValueError, "history must be"):
                    _validate_numeric_tool_args("mean_sign", {"history": malformed}, ["numeric_context"], {})

    def test_accepts_direct_reference_and_numeric_list(self):
        _validate_numeric_tool_args("mean_sign", {"history": {"$step": 0, "path": ["history"]}}, ["numeric_context"], {})
        _validate_numeric_tool_args("numeric_context", {"history": [2, 4, 6], "window": 3}, [], {})

    def test_comparison_requires_scalar_not_whole_object(self):
        args = {"left": {"$step": 0}, "right": 1, "abs_tol": 0.0001, "rel_tol": 0}
        with self.assertRaisesRegex(ValueError, "scalar numbers"):
            _validate_numeric_tool_args("compare_numeric", args, ["mean_sign"], {})
        args["left"]["path"] = ["prediction"]
        _validate_numeric_tool_args("compare_numeric", args, ["mean_sign"], {})


class TypedPlanContractTest(unittest.TestCase):
    def test_compiles_explicit_reference_without_inventing_values(self):
        from bean.runtime.typed_plan_contract import compile_typed_args
        self.assertEqual(compile_typed_args("mean_sign", {"history": "@0.history"}),
                         {"history": {"$step": 0, "path": ["history"]}})
        self.assertEqual(compile_typed_args("compare_numeric", {"left": "@1.prediction", "right": 1}),
                         {"left": {"$step": 1, "path": ["prediction"]}, "right": 1})
        self.assertEqual(compile_typed_args("reason", {"query": "@0.history"}),
                         {"query": "@0.history"})
        with self.assertRaises(ValueError):
            compile_typed_args("mean_sign", {"history": "@0.prediction"})

    def test_schema_only_exposes_registered_tools(self):
        from bean.runtime.typed_plan_contract import plan_schema
        options = plan_schema(["mean_sign"])["properties"]["steps"]["items"]["anyOf"]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["properties"]["tool"]["enum"], ["mean_sign"])
        args = options[0]["properties"]["args"]
        self.assertEqual(args["required"], ["history"])
        self.assertIn("@0.history", args["properties"]["history"]["anyOf"][1]["enum"])

    def test_schema_transport(self):
        from bean.runtime.typed_plan_contract import plan_schema
        requests = []
        def request(req, timeout):
            requests.append(json.loads(req.data))
            return io.BytesIO(json.dumps({
                "model": "qwen2.5:7b", "id": "test",
                "choices": [{"message": {"content": '{"steps":[]}'}}]
            }).encode())
        provider = LocalLlamaCppProvider(base_url="http://127.0.0.1:11434",
                                         model_name="qwen2.5:7b", requester=request)
        schema = plan_schema(["mean_sign"])
        _model_response(provider, "plan", None, json_object=True, schema=schema)
        self.assertEqual(requests[-1]["response_format"]["json_schema"]["schema"], schema)


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

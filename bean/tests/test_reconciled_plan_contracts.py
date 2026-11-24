"""Regression coverage for recovered native reference and JSON transport fixes."""
import io
import json
import unittest

from bean.runtime.plan_contracts import (compile_arguments, preflight, read_path,
                                         preview, validate_skill_selection)
from bean.learning.reasoning_service import _model_response
from bean.reasoning.local_llamacpp_provider import LocalLlamaCppProvider


class PlanContractRecoveryTests(unittest.TestCase):
    def test_scalar_paths_rejected_before_execution(self):
        for tool, field in (("mean_sign", "prediction"), ("numeric_context", "mean"),
                            ("compare_numeric", "left")):
            with self.subTest(tool=tool):
                with self.assertRaisesRegex(ValueError, "scalar"):
                    preflight("compare_numeric", {
                        "left": {"$step": 0, "path": [field, 0]}, "right": 1,
                        "abs_tol": 0, "rel_tol": 0}, {}, [tool])

    def test_incompatible_direct_and_nested_outputs_rejected(self):
        for ref in ({"$step": 0}, {"$step": 0, "path": ["prediction"]}):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, "incompatible output shape"):
                    preflight("mean_sign", {"history": ref}, {}, ["last_sign"])
        with self.assertRaisesRegex(ValueError, "incompatible history element"):
            preflight("mean_sign", {
                "history": [{"$step": 0, "path": ["history"]}]}, {}, ["numeric_context"])

    def test_valid_references_and_runtime_bounds(self):
        preflight("mean_sign", {"history": {"$step": 0, "path": ["history"]}},
                  {}, ["numeric_context"])
        preflight("compare_numeric", {
            "left": {"$step": 0, "path": ["history", 2]}, "right": 1,
            "abs_tol": 0, "rel_tol": 0}, {}, ["numeric_context"])
        with self.assertRaises(ValueError):
            read_path({"history": [1]}, ["history", 2])

    def test_recovery_json_object_keys_are_strings(self):
        data = {"__recovery": {"completed": {"0": {"mean": 4}}}}
        self.assertEqual(read_path(data, ["__recovery", "completed", "0", "mean"]), 4)
        with self.assertRaises(ValueError):
            read_path(data, ["__recovery", "completed", 0, "mean"])

    def test_explicit_typed_reference_compiles_without_executing_tools(self):
        steps = [
            {"tool": "numeric_context", "args": {"history": [1, 2]}},
            {"tool": "mean_sign", "args": {"history": "@0.history"}},
            {"tool": "compare_numeric", "args": {
                "left": "@1.prediction", "right": 1, "abs_tol": 0, "rel_tol": 0}},
            {"tool": "reason", "args": {"query": "@0.history"}},
        ]
        result = compile_arguments(json.dumps({"steps": steps}), {},
                                   {s["tool"] for s in steps})
        self.assertEqual(result[1]["args"]["history"], {"$step": 0, "path": ["history"]})
        self.assertEqual(result[2]["args"]["left"], {"$step": 1, "path": ["prediction"]})
        self.assertEqual(result[3]["args"]["query"], "@0.history")
        steps[1]["args"]["history"] = "@0.mean"
        with self.assertRaisesRegex(ValueError, "incompatible output shape"):
            compile_arguments(json.dumps({"steps": steps}), {}, {s["tool"] for s in steps})

    def test_retained_skill_identity_and_deferred_hash(self):
        skills = {"weighted_mean": {}, "interval_overlap": {}}
        transfer = {"weighted_mean": object()}
        with self.assertRaisesRegex(ValueError, "installed catalog"):
            validate_skill_selection("retained_skill_inventory", {"skill_id": "invented"},
                                     skills, transfer)
        with self.assertRaisesRegex(ValueError, "installed catalog"):
            validate_skill_selection("evaluate_skill", {
                "skill_id": "interval_overlap", "objective_sha256": "a" * 64}, skills, transfer)
        with self.assertRaisesRegex(ValueError, "objective_sha256"):
            validate_skill_selection("evaluate_skill", {
                "skill_id": "weighted_mean", "objective_sha256": "guess"}, skills, transfer)
        args = {"skill_id": "weighted_mean",
                "objective_sha256": {"$step": 0, "path": ["skills", 0, "objective_sha256"]}}
        validate_skill_selection("evaluate_skill",
                                 preview(args, {}, ["retained_skill_inventory"]), skills, transfer)
        validate_skill_selection("evaluate_skill", {
            "skill_id": "weighted_mean", "objective_sha256": "a" * 64}, skills, transfer)

    def test_unknown_extension_shape_is_deferred(self):
        preflight("mean_sign", {"history": {"$step": 0, "path": ["data", "history"]}},
                  {}, ["extension_tool"])


class StructuredLocalTransportTests(unittest.TestCase):
    def test_json_schema_and_unstructured_requests_remain_distinct(self):
        requests = []

        def requester(request, timeout):
            requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({
                "model": "qwen2.5:7b", "id": "fixture",
                "choices": [{"message": {"content": '{"steps":[]}'}}]
            }).encode())

        provider = LocalLlamaCppProvider(base_url="http://127.0.0.1:11434",
                                         model_name="qwen2.5:7b", requester=requester)
        self.assertEqual(json.loads(_model_response(
            provider, "plan", None, json_object=True)[0]), {"steps": []})
        self.assertEqual(requests[-1]["response_format"], {"type": "json_object"})
        self.assertEqual(requests[-1]["temperature"], 0)
        schema = {"type": "object"}
        _model_response(provider, "plan", None, json_object=True, schema=schema)
        self.assertEqual(requests[-1]["response_format"]["json_schema"]["schema"], schema)
        provider.complete("hello")
        self.assertNotIn("response_format", requests[-1])

    def test_generic_provider_still_works(self):
        class Model:
            model_id = "fixture"
            provider_kind = "synthetic_fixture"

            def complete(self, prompt, context):
                return '{"steps":[]}'

        self.assertEqual(_model_response(Model(), "plan", None, json_object=True)[0],
                         '{"steps":[]}')


if __name__ == "__main__":
    unittest.main()

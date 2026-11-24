"""Regression for model-generated scalar paths and recovery evidence keys."""
import unittest

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


if __name__ == "__main__":
    unittest.main()

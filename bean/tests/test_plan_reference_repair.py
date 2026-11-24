import unittest

from bean.runtime.native_orchestration import _path, _preflight_references


class PlanReferenceRepairTests(unittest.TestCase):
    def test_recovery_json_object_keys_are_resolved(self):
        inputs = {"__recovery": {"completed": {"0": {"mean": 4.0},
                                                 "1": {"prediction": 1}}}}
        for key in (0, "0"):
            path = ["__recovery", "completed", key, "mean"]
            self.assertEqual(_path(inputs, path), 4.0)
            _preflight_references({"left": {"$input": path}}, inputs, [])
        with self.assertRaisesRegex(ValueError, "available keys"):
            _preflight_references({"$input": ["__recovery", "completed", "2"]},
                                  inputs, [])

    def test_invalid_scalar_reference_rejected_before_execution(self):
        tools = ["numeric_context", "mean_sign"]
        with self.assertRaisesRegex(ValueError, "descends into scalar"):
            _preflight_references({"left": {"$step": 1, "path": ["prediction", 0]}},
                                  {}, tools)
        _preflight_references({"left": {"$step": 1, "path": ["prediction"]},
                               "right": {"$step": 0, "path": ["mean"]}}, {}, tools)

    def test_array_indices_and_unknown_output(self):
        _preflight_references({"$step": 0, "path": ["history", 2]}, {},
                              ["numeric_context"])
        with self.assertRaises(ValueError):
            _preflight_references({"$step": 0, "path": ["history", "2"]}, {},
                                  ["numeric_context"])
        _preflight_references({"$step": 0, "path": ["custom"]}, {}, ["unknown_tool"])
        with self.assertRaises(ValueError):
            _path({"history": [1]}, ["history", 2])


if __name__ == "__main__":
    unittest.main()

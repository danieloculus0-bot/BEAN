import unittest

from bean.runtime.native_orchestration import _path, _preflight_references, _check_tool_arguments


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

    def test_named_arguments_and_retained_skill_identity(self):
        skills = {"weighted_mean": {}, "interval_overlap": {}}
        transfer = {"weighted_mean": object()}
        with self.assertRaisesRegex(ValueError, "requires named arguments"):
            _check_tool_arguments("mean_sign", {"$step": 0, "path": ["history"]})
        with self.assertRaisesRegex(ValueError, "invalid type"):
            _check_tool_arguments("mean_sign", {"history": 4}, resolved=True)
        with self.assertRaisesRegex(ValueError, "must be one of"):
            _check_tool_arguments("retained_skill_inventory", {"skill_id": "invented"}, skills, transfer)
        with self.assertRaisesRegex(ValueError, "must be one of"):
            _check_tool_arguments("evaluate_skill", {"skill_id": "interval_overlap", "objective_sha256": "a"*64}, skills, transfer)
        with self.assertRaisesRegex(ValueError, "exact objective_sha256"):
            _check_tool_arguments("evaluate_skill", {"skill_id": "weighted_mean", "objective_sha256": "guess"}, skills, transfer)
        _check_tool_arguments("mean_sign", {"history": {"$step": 0, "path": ["history"]}})
        _check_tool_arguments("evaluate_skill", {"skill_id": "weighted_mean", "objective_sha256": {"$step": 0, "path": ["skills", 0, "objective_sha256"]}}, skills, transfer)
        _check_tool_arguments("evaluate_skill", {"skill_id": "weighted_mean", "objective_sha256": "a"*64}, skills, transfer, resolved=True)


if __name__ == "__main__":
    unittest.main()

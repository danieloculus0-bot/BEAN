"""Recovery observations must survive multiple failed child plans."""
import json
import unittest

from bean.runtime.orchestration_recovery import _inherit_observations


class RecoveryAncestorObservationsTest(unittest.TestCase):
    def test_three_generations_preserve_colliding_step_ids(self):
        root = _inherit_observations({
            "parent": "root", "completed": {"0": {"mean": 4}}, "failures": []
        }, {})
        child = _inherit_observations({
            "parent": "child", "completed": {"0": {"prediction": 1}}, "failures": []
        }, json.loads(json.dumps(root)))
        grandchild = _inherit_observations({
            "parent": "grandchild", "completed": {}, "failures": []
        }, json.loads(json.dumps(child)))
        self.assertEqual(grandchild["completed_by_plan"], {
            "root": {"0": {"mean": 4}},
            "child": {"0": {"prediction": 1}},
            "grandchild": {},
        })
        self.assertEqual(grandchild["completed"], {})
        self.assertEqual(root["completed_by_plan"], {"root": {"0": {"mean": 4}}})

    def test_pre_migration_evidence_and_failed_output(self):
        old = {"parent": "old", "completed": {"1": {"value": 7}},
               "failures": [{"output": {"value": 99}}]}
        new = _inherit_observations({
            "parent": "new", "completed": {}, "failures": [{"output": 8}]
        }, old)
        self.assertEqual(new["completed_by_plan"]["old"], {"1": {"value": 7}})
        self.assertNotIn("99", json.dumps(new["completed_by_plan"]))
        self.assertIn("STEP_KEY", new["reference_contract"])


if __name__ == "__main__":
    unittest.main()

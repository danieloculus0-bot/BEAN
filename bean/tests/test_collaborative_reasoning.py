import unittest
from bean.runtime.collaborative_reasoning import deliberate


class RecordingModel:
    model_id = "test-model"
    provider_kind = "synthetic_fixture"

    def __init__(self):
        self.calls = []

    def complete(self, prompt, context):
        self.calls.append((prompt, context))
        return ["candidate 17", "candidate 17 conflicts with observed value",
                "revised 19; verify with a separate calculation"][len(self.calls)-1]


class CollaborativeReasoningTests(unittest.TestCase):
    def test_roles_receive_previous_work_and_observations(self):
        model = RecordingModel()
        result = deliberate(model, objective="Reconcile the calculation",
                            observations={"measured": 19})
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual([x["role"] for x in result["roles"]],
                         ["proposer", "critic", "reviser"])
        self.assertIn("candidate 17", model.calls[1][0])
        self.assertIn("conflicts with observed value", model.calls[2][0])
        self.assertIn('"measured": 19', model.calls[2][0])
        self.assertIn("revised 19", result["revision"])
        self.assertFalse(result["independent_outcome_verified"])
        self.assertTrue(all(len(x["sha256"]) == 64 for x in result["roles"]))

    def test_missing_model_not_success(self):
        with self.assertRaises(ValueError):
            deliberate(None, objective="A task")


if __name__ == "__main__":
    unittest.main()

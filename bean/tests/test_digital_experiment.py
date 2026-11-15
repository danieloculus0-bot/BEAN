"""Synthetic offline checks for the optional native experiment adapter."""
from bean.runtime.digital_experiment import make_local_reasoning_experiment


class Core:
    def __init__(self, observation):
        self.observation = observation
        self.calls = []

    def reason_local(self, **kwargs):
        self.calls.append(kwargs)
        return self.observation


def goal(capability="native_reason_local"):
    return {"action_detail": {
        "capability": capability,
        "inputs": {"domain": "synthetic", "task_ref": "case-1", "query": "a?"},
        "expected_output": {"answer": "yes"},
    }}


def test_real_core_method_called_but_expected_not_ground_truth():
    core = Core({"status": "locally_solved", "answer": "yes"})
    result = make_local_reasoning_experiment(core)(goal())
    assert result["status"] == "unverified"
    assert result["prediction_matches_expected"] is True
    assert result["independent_outcome_verified"] is False
    assert core.calls == [{"domain": "synthetic", "task_ref": "case-1", "query": "a?"}]


def test_wrong_prediction_is_retained_as_negative_evidence():
    core = Core({"status": "locally_solved", "answer": "no"})
    result = make_local_reasoning_experiment(core)(goal())
    assert result["prediction_matches_expected"] is False
    assert result["status"] == "unverified"


def test_abstention_and_unknown_capability_never_claim_success():
    core = Core({"status": "unknown", "reason": "no_rule"})
    handler = make_local_reasoning_experiment(core)
    assert handler(goal())["reason"] == "native_reasoner_abstained"
    assert handler(goal("arbitrary_shell"))["status"] == "unknown"
    assert len(core.calls) == 1


def test_invalid_inputs_do_not_call_core():
    core = Core({"status": "locally_solved", "answer": "yes"})
    item = goal()
    item["action_detail"]["inputs"]["query"] = "x" * 501
    assert make_local_reasoning_experiment(core)(item)["status"] == "unknown"
    assert core.calls == []

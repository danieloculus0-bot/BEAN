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

def test_registered_goalcycle_persists_unverified_outcome_without_replay(tmp_path):
    import json
    from bean.cognition.goal_state import (
        ActionType, ApprovalRequired, GoalProposal, GoalStateEngine,
    )
    from bean.memory.store import _local, get_store, init_store
    from bean.runtime.goal_cycle import GoalCycle

    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "digital_goal.sqlite"))
    try:
        item = GoalProposal(
            "investigate_open_question", ActionType.RUN_EXPERIMENT,
            "synthetic held-out question", 3, ApprovalRequired.NONE,
            action_detail=goal()["action_detail"],
        )
        GoalStateEngine()._persist(item, "synthetic-session")
        core = Core({"status": "locally_solved", "answer": "yes"})
        cycle = GoalCycle({
            "run_experiment": make_local_reasoning_experiment(core),
        })
        receipt = cycle.poll_due()[0]
        assert receipt["status"] == "n/a"
        row = cycle.history()[0]
        saved = json.loads(row["result_json"])
        assert saved["independent_outcome_verified"] is False
        assert saved["prediction_matches_expected"] is True
        assert row["proposal_id"] == item.proposal_id
        restarted = GoalCycle({
            "run_experiment": make_local_reasoning_experiment(core),
        })
        assert restarted.recover_interrupted() == 0
        assert restarted.poll_due() == []
        assert len(core.calls) == 1
    finally:
        get_store().close()

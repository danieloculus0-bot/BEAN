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


def test_host_evaluator_receives_prediction_not_expected_label():
    calls = []
    core = Core({"status": "locally_solved", "answer": "no"})
    def oracle(inputs, prediction):
        calls.append((inputs, prediction))
        return {"verdict": "incorrect", "evidence_ref": "synthetic-oracle:case-1"}
    item = goal()
    item["action_detail"]["expected_output"]["answer"] = "secret-label"
    result = make_local_reasoning_experiment(core, evaluator=oracle)(item)
    assert calls == [({"domain": "synthetic", "task_ref": "case-1",
                       "query": "a?"}, "no")]
    assert result["evaluator_receipt"] == {
        "verdict": "incorrect", "evidence_ref": "synthetic-oracle:case-1",
        "independently_audited": False,
        "subject_sha256": result["evaluation_subject_sha256"]}
    assert result["status"] == "unverified"
    assert result["independent_outcome_verified"] is False


def test_invalid_or_failed_evaluator_never_promotes_to_success():
    core = Core({"status": "locally_solved", "answer": "yes"})
    for evaluator, reason in [
        (lambda inputs, answer: {"verdict": "correct"}, "invalid_evaluator_receipt"),
        (lambda inputs, answer: {"verdict": "correct", "evidence_ref": ""}, "invalid_evaluator_receipt"),
    ]:
        result = make_local_reasoning_experiment(core, evaluator=evaluator)(goal())
        assert result["status"] == "unverified"
        assert result["evaluator_receipt"]["reason"] == reason
    def broken(inputs, answer):
        raise RuntimeError("synthetic evaluator outage")
    result = make_local_reasoning_experiment(core, evaluator=broken)(goal())
    assert result["evaluator_receipt"]["reason"] == "evaluator_failed"
    assert result["independent_outcome_verified"] is False


def test_abstention_does_not_call_oracle():
    calls = []
    core = Core({"status": "unknown"})
    result = make_local_reasoning_experiment(
        core, evaluator=lambda inputs, answer: calls.append(answer))(goal())
    assert result["status"] == "unverified"
    assert calls == []


def test_oversized_core_answer_never_reaches_evaluator():
    """A locally solved result must not bypass the experiment output budget."""
    calls = []
    answer = "x" * 1001
    core = Core({"status": "locally_solved", "answer": answer})
    result = make_local_reasoning_experiment(
        core, evaluator=lambda inputs, prediction: calls.append(prediction))(goal())
    assert result["status"] == "unverified"
    assert result["reason"] == "core_answer_exceeds_bound"
    assert result["independent_outcome_verified"] is False
    assert len(result["observed_answer_sha256"]) == 64
    assert calls == []


def test_answer_at_bound_still_reaches_evaluator():
    calls = []
    core = Core({"status": "locally_solved", "answer": "x" * 1000})
    result = make_local_reasoning_experiment(
        core, evaluator=lambda inputs, prediction: (
            calls.append(prediction) or {"verdict": "unknown", "evidence_ref": "synthetic:bound"}
        ))(goal())
    assert len(calls) == 1 and len(calls[0]) == 1000
    assert result["status"] == "unverified"

def test_evaluator_receipt_digest_binds_exact_prediction_and_inputs():
    """A claimed verdict must identify which prediction was evaluated."""
    import hashlib
    import json
    core = Core({"status": "locally_solved", "answer": "yes"})
    oracle = lambda inputs, answer: {
        "verdict": "correct", "evidence_ref": "synthetic:oracle-1"}
    handler = make_local_reasoning_experiment(core, evaluator=oracle)
    first = handler(goal())
    subject = {"inputs": goal()["action_detail"]["inputs"], "prediction": "yes"}
    digest = hashlib.sha256(json.dumps(
        subject, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    assert first["evaluation_subject_sha256"] == digest
    assert first["evaluator_receipt"]["subject_sha256"] == digest
    assert first["independent_outcome_verified"] is False

    core.observation = {"status": "locally_solved", "answer": "no"}
    changed_prediction = handler(goal())
    assert changed_prediction["evaluation_subject_sha256"] != digest
    assert changed_prediction["evaluator_receipt"]["subject_sha256"] != digest

    changed_inputs = goal()
    changed_inputs["action_detail"]["inputs"]["query"] = "different?"
    changed_query = handler(changed_inputs)
    assert changed_query["evaluation_subject_sha256"] != changed_prediction["evaluation_subject_sha256"]
    assert changed_query["status"] == "unverified"

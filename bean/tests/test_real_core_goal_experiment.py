"""Real, disposable BEAN Core experiment: retained rule versus cold start.

This tests actual NativeReasoningService, GoalCycle, and both existing SQLite
owners. Synthetic ground truth is independently computed by the test, not
trusted from the proposed goal. This is a narrow symbolic transfer test.
"""
import json

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine,
)
from bean.learning.reasoning_service import NativeReasoningService
from bean.memory.store import _local, get_store, init_store
from bean.runtime.digital_experiment import make_local_reasoning_experiment
from bean.runtime.goal_cycle import GoalCycle


def _reset_store(path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(path))


def _experiment(query, answer, task_ref):
    return {
        "capability": "native_reason_local",
        "inputs": {"domain": "synthetic-transfer", "task_ref": task_ref,
                   "query": query},
        "expected_output": {"answer": answer},
    }


def test_real_native_core_rule_survives_restart_and_changes_goal_outcome(tmp_path):
    # All examples and the withheld case are distinct. The independent
    # oracle is digit-descending order, not a model-provided expected answer.
    examples = [
        {"question": "A1 B3 C2", "answer": "BCA"},
        {"question": "D2 E5 F1", "answer": "EDF"},
        {"question": "G4 H1 I3", "answer": "GIH"},
    ]
    heldout = "J3 K8 L1"
    oracle = "".join(k for k, _ in sorted(
        [("J", 3), ("K", 8), ("L", 1)], key=lambda pair: -pair[1]))
    assert oracle == "KJL"
    _reset_store(tmp_path / "goal.sqlite")
    cold = NativeReasoningService(tmp_path / "cold_reasoning.sqlite")
    learned = NativeReasoningService(tmp_path / "learned_reasoning.sqlite")
    try:
        # Paired cold-start baseline uses the identical query and no provider.
        cold_result = make_local_reasoning_experiment(cold)({
            "action_detail": _experiment(heldout, oracle, "cold")})
        assert cold_result["status"] == "unverified"
        assert cold_result["reason"] == "native_reasoner_abstained"

        learned_result = learned.learn_local(
            domain="synthetic-transfer", task_ref="training",
            examples=examples, evidence_refs=["synthetic:seed-0:development"])
        assert learned_result["status"] == "learned_local_rule"
        learned.close()

        # Actual fresh service instance restores the SHA journal from disk.
        learned = NativeReasoningService(tmp_path / "learned_reasoning.sqlite")
        proposal = GoalProposal(
            "investigate_open_question", ActionType.RUN_EXPERIMENT,
            "synthetic withheld digit-ordering", 3, ApprovalRequired.NONE,
            action_detail=_experiment(heldout, oracle, "heldout-1"))
        GoalStateEngine()._persist(proposal, "synthetic-restart-session")
        cycle = GoalCycle({
            "run_experiment": make_local_reasoning_experiment(learned)})
        receipts = cycle.poll_due()
        assert len(receipts) == 1
        assert receipts[0]["status"] == "n/a"
        row = cycle.history()[0]
        observed = json.loads(row["result_json"])
        assert observed["status"] == "unverified"
        assert observed["independent_outcome_verified"] is False
        assert observed["prediction_matches_expected"] is True
        assert observed["observed_answer"] == oracle
        assert row["proposal_id"] == proposal.proposal_id
        assert learned.reason_local(
            domain="synthetic-transfer", task_ref="heldout-2",
            query="M2 N9 O4")["answer"] == "NOM"

        # Reopening both SQLite owners must not re-execute a completed goal.
        learned.close()
        learned = NativeReasoningService(tmp_path / "learned_reasoning.sqlite")
        get_store().close()
        _reset_store(tmp_path / "goal.sqlite")
        restarted = GoalCycle({
            "run_experiment": make_local_reasoning_experiment(learned)})
        assert restarted.recover_interrupted() == 0
        assert restarted.poll_due() == []
        assert len(restarted.history()) == 1
        assert json.loads(restarted.history()[0]["result_json"]) == observed
        assert learned.reason_local(
            domain="synthetic-transfer", task_ref="heldout-3",
            query="P7 Q1 R5")["answer"] == "PRQ"
    finally:
        cold.close()
        learned.close()
        get_store().close()

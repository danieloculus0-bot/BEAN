"""Negative control: a caller's expected answer is not an independent oracle.

Exercises actual BEAN native reasoning and GoalCycle with disposable SQLite.
A deliberately false expected answer must not earn verified learning credit.
"""
import json

from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, GoalStateEngine
from bean.learning.reasoning_service import NativeReasoningService
from bean.memory.store import _local, get_store, init_store
from bean.runtime.digital_experiment import make_local_reasoning_experiment
from bean.runtime.goal_cycle import GoalCycle


def test_false_expected_answer_cannot_become_verified_outcome(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    db = tmp_path / "goals.sqlite"
    init_store(str(db))
    core = NativeReasoningService(tmp_path / "reasoning.sqlite")
    try:
        examples = [
            {"question": "A1 B3 C2", "answer": "BCA"},
            {"question": "D2 E5 F1", "answer": "EDF"},
            {"question": "G4 H1 I3", "answer": "GIH"},
        ]
        assert core.learn_local(
            domain="synthetic-transfer", task_ref="negative-control-training",
            examples=examples, evidence_refs=["synthetic:negative-control"]
        )["status"] == "learned_local_rule"
        query = "J3 K8 L1"
        # Independent oracle: sort labels by descending numeric suffix.
        pairs = [("J", 3), ("K", 8), ("L", 1)]
        oracle = "".join(label for label, _ in sorted(pairs, key=lambda p: -p[1]))
        assert oracle == "KJL"
        deliberately_wrong = "JKL"
        proposal = GoalProposal(
            "investigate_open_question", ActionType.RUN_EXPERIMENT,
            "negative-control wrong host expectation", 3, ApprovalRequired.NONE,
            action_detail={
                "capability": "native_reason_local",
                "inputs": {"domain": "synthetic-transfer",
                           "task_ref": "negative-control-heldout", "query": query},
                "expected_output": {"answer": deliberately_wrong},
            },
        )
        GoalStateEngine()._persist(proposal, "negative-control-session")
        cycle = GoalCycle({"run_experiment": make_local_reasoning_experiment(core)})
        assert len(cycle.poll_due()) == 1
        observed = json.loads(cycle.history()[0]["result_json"])
        assert observed["observed_answer"] == oracle
        assert observed["prediction_matches_expected"] is False
        assert observed["independent_outcome_verified"] is False
        assert observed["status"] == "unverified"
        # Reopening both stores must preserve negative evidence without replay.
        core.close()
        core = NativeReasoningService(tmp_path / "reasoning.sqlite")
        get_store().close()
        _local.conn = None
        init_store(str(db))
        reopened = GoalCycle({"run_experiment": make_local_reasoning_experiment(core)})
        assert reopened.poll_due() == []
        assert json.loads(reopened.history()[0]["result_json"]) == observed
    finally:
        core.close()
        get_store().close()

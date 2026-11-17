"""Regression for explicit context-isolated experience, not general learning proof."""
import json

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine,
)
from bean.memory.store import _local, get_store, init_store
from bean.runtime.goal_cycle import GoalCycle


def test_context_reversal_retains_failures_without_cross_context_penalty(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    path = str(tmp_path / "context.sqlite")
    init_store(path)
    try:
        owner = GoalStateEngine()
        def propose(context, n):
            item = GoalProposal(
                "experiment", ActionType.UPDATE_MODELS, "synthetic feedback",
                2, ApprovalRequired.NONE,
                action_detail={"learning_context": context, "trial": n},
            )
            owner._persist(item, "context-test")
            return item

        # Same registered action has opposite observed outcomes in two
        # independent digital environments. These are execution receipts,
        # not verified factual learning or an AGI score.
        cycle = GoalCycle({"update_models": lambda g: {
            "status": "failed" if g["action_detail"]["learning_context"] == "world-a"
            else "verified"
        }})
        for i in range(6):
            propose("world-a", i)
            assert cycle.poll_due()[0]["status"] == "failed"
        a = propose("world-a", 7)
        b = propose("world-b", 0)
        # Equal priority: unseen world-b must retain its own novelty, rather
        # than inherit six failures from world-a.
        receipt = cycle.poll_due()[0]
        assert receipt["proposal_id"] == b.proposal_id
        assert receipt["decision"]["outcome_scope"] == "explicit_context"
        assert receipt["decision"]["prior_attempts"] == 0
        assert receipt["decision"]["observed_failures"] == 0
        assert receipt["status"] == "success"
        assert get_store().fetchone(
            "SELECT status FROM cognition_goal_proposals WHERE proposal_id=?",
            (a.proposal_id,)
        )["status"] == "pending"

        get_store().close()
        init_store(path)
        resumed = GoalCycle({"update_models": lambda g: {"status": "failed"}})
        assert resumed.recover_interrupted() == 0
        next_receipt = resumed.poll_due()[0]
        assert next_receipt["proposal_id"] == a.proposal_id
        assert next_receipt["decision"]["prior_attempts"] == 6
        assert next_receipt["decision"]["observed_failures"] == 6
        assert next_receipt["decision"]["observed_successes"] == 0
        assert next_receipt["decision"]["context_sha256"] != receipt["decision"]["context_sha256"]
        assert len(resumed.history()) == 8
    finally:
        get_store().close()


def test_untagged_goal_retains_legacy_pooled_history(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "legacy.sqlite"))
    try:
        owner = GoalStateEngine()
        cycle = GoalCycle({"update_models": lambda _: {"status": "failed"}})
        for n in range(2):
            item = GoalProposal(f"legacy-{n}", ActionType.UPDATE_MODELS,
                                "test", 2, ApprovalRequired.NONE)
            owner._persist(item, "legacy")
            receipt = cycle.poll_due()[0]
            assert receipt["decision"]["outcome_scope"] == "pooled"
            assert receipt["decision"]["prior_attempts"] == n
    finally:
        get_store().close()

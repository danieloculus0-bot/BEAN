"""Synthetic native GoalCycle physics dispatch and SQLite restart regression.

This checks real BEAN deterministic solver execution through an explicitly registered
capability. It does NOT demonstrate autonomous solver selection, learned physics,
independent feedback, or consciousness. No private data or hardware.
"""
import hashlib
import json
import math

from bean.cognition.goal_state import ActionType, ApprovalRequired, GoalProposal, GoalStateEngine
from bean.engineering.spaceflight import REQUEST_SCHEMA, solve_spaceflight_reference
from bean.memory.store import _local, get_store, init_store
from bean.runtime.goal_cycle import GoalCycle


def test_native_goalcycle_executes_physics_and_retains_sha_receipt(tmp_path):
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    init_store(str(tmp_path / "physics_goal.sqlite"))
    try:
        proposal = GoalProposal(
            "synthetic physics cross-domain reference", ActionType.RUN_EXPERIMENT,
            "evaluate a declared projectile request", 1, ApprovalRequired.NONE,
        )
        GoalStateEngine()._persist(proposal, "synthetic-physics-session")
        request = {
            "schema": REQUEST_SCHEMA, "calculation": "earth_projectile",
            "parameters": {
                "launch_speed_m_s": 24.0, "angle_deg": 37.0,
                "initial_height_m": 3.0, "gravity_m_s2": 9.81,
                "linear_drag_s_inv": 0.12,
            },
        }
        calls = []
        def physics_capability(_goal):
            calls.append("executed")
            answer = solve_spaceflight_reference(request)
            result = answer["result"]
            assert answer["calculation"] == "earth_projectile"
            assert math.isfinite(result["flight_time_s"])
            assert result["flight_time_s"] > 0
            assert result["horizontal_range_m"] > 0
            assert answer["independently_validated"] is False
            # A host-side deterministic calculation, not a learned prediction.
            return {"status": "verified", "reference": answer,
                    "evaluation_scope": "deterministic_physics_reference_only"}
        emitted = []
        cycle = GoalCycle({"run_experiment": physics_capability},
                          event_sink=emitted.append)
        receipts = cycle.poll_due()
        assert len(receipts) == 1
        assert receipts[0]["status"] == "success"
        assert calls == ["executed"]
        assert emitted == receipts
        stored = get_store().fetchone(
            "SELECT result_json FROM bean_goal_runs WHERE proposal_id=?",
            (proposal.proposal_id,),
        )["result_json"]
        assert json.loads(stored)["reference"]["calculation"] == "earth_projectile"
        digest = hashlib.sha256(stored.encode("utf-8")).hexdigest()
        assert receipts[0]["result_sha256"] == digest

        path = get_store().db_path
        get_store().close()
        init_store(path)
        restarted = GoalCycle({"run_experiment": lambda _: (_ for _ in ()).throw(
            AssertionError("physics capability must not replay"))})
        assert restarted.recover_interrupted() == 0
        assert restarted.poll_due() == []
        history = restarted.history()
        assert len(history) == 1
        assert hashlib.sha256(history[0]["result_json"].encode("utf-8")).hexdigest() == digest
        assert calls == ["executed"]
    finally:
        get_store().close()
        _local.conn = None

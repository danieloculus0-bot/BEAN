"""Reproducible synthetic Core learning/goal/feedback/restart probe.

This host authors the plan and independently grades a tiny declared ordering
task. It is an integration probe, not autonomous plan invention, a new learning
algorithm, or evidence of superiority over a grammar-matched control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from bean.cognition.goal_state import (
    ActionType, ApprovalRequired, GoalProposal, GoalStateEngine,
)
from bean.learning.reasoning_service import NativeReasoningService
from bean.memory.event_logger import EventType, Source, get_recent_events, log_event
from bean.modules.builtin import memory_recall
from bean.runtime.bootstrap import shutdown_bean, start_bean
from bean.runtime.digital_experiment import make_local_reasoning_experiment
from bean.runtime.goal_cycle import GoalCycle
from bean.runtime.tick_handlers import build_default_handlers


def run_probe(output_dir) -> dict:
    """Run on new synthetic-only databases; never reset an existing directory."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    ctx = start_bean(db_path=str(output / "core.sqlite"), silent=True)
    core = NativeReasoningService(output / "reasoning.sqlite")
    cold = NativeReasoningService(output / "cold.sqlite")
    trace = []
    examples = [{"question": "A1 B3 C2", "answer": "BCA"},
                {"question": "D2 E5 F1", "answer": "EDF"},
                {"question": "G4 H1 I3", "answer": "GIH"}]
    observed = log_event(ctx["session_uuid"], EventType.OBSERVATION,
        "Synthetic ordering examples observed", Source.SYSTEM, data={"examples": examples})
    query = "J3 K8 L1"
    oracle = "".join(k for k, _ in sorted(
        [("J", 3), ("K", 8), ("L", 1)], key=lambda pair: -pair[1]))
    inputs = {"domain": "plan-ordering", "task_ref": "withheld", "query": query}

    def learn(goal):
        recalled = memory_recall({"limit": 20}, ctx)
        source = next(e for e in recalled["events"] if e["id"] == observed)
        result = core.learn_local(domain="plan-ordering", task_ref="development",
            examples=source["data"]["examples"], evidence_refs=[f"event:{observed}"])
        trace.append({"stage": "retrieval_hypothesis_memory",
                      "source_event_id": observed, **result})
        return {"status": "success" if result.get("lesson_retained") else "unknown",
                "learning_result": result}

    def predict(goal):
        result = make_local_reasoning_experiment(core)(goal)
        trace.append({"stage": "action_evaluation", **result})
        if result.get("observed_answer") is None:
            return {"status": "unknown", "native_result": result}
        return {"status": "success" if result["observed_answer"] == oracle else "failed",
                "native_result": result, "evaluation_scope": "synthetic_host_oracle_only",
                "independent_outcome_verified": False}

    def feedback(goal):
        row = next(r for r in cycle.history() if r["action_type"] == "run_experiment")
        original = json.loads(row["result_json"])["native_result"]
        result = core.feedback(receipt_id=original["core_receipt_id"],
            expected=oracle, evidence_refs=["synthetic:heldout-oracle"],
            adjustment_hypothesis="Recheck the numeric ordering against observed outcomes")
        trace.append({"stage": "feedback_memory_update", **result})
        return {"status": "success", "feedback": result}

    def event(receipt):
        log_event(ctx["session_uuid"], EventType.OBSERVATION,
            "Synthetic planned action outcome", Source.SYSTEM,
            subtype="autonomous_goal_cycle", data=receipt)

    def template(name, action, priority, detail=None):
        return GoalProposal(name, action, "synthetic plan probe", priority,
                            ApprovalRequired.NONE, action_detail=detail)

    try:
        cold_before = cold.reason_local(**inputs)
        templates = [template("learn", ActionType.PRACTICE_SKILL, 9),
            template("predict", ActionType.RUN_EXPERIMENT, 1, {
                "capability": "native_reason_local", "inputs": inputs,
                "expected_output": {"answer": "deliberately-false-host-label"}}),
            template("feedback", ActionType.RUN_REFLECTION, 1)]
        plan = GoalStateEngine().propose_plan(ctx["session_uuid"], "cognition-probe", templates)
        actions = {"practice_skill": learn, "run_experiment": predict, "run_reflection": feedback}
        cycle = GoalCycle(actions, event_sink=event)
        build_default_handlers(goal_cycle=cycle).run_due(1, ctx["session_uuid"], ctx)
        first_progress = cycle.plan_status("cognition-probe")
        first_session = ctx["session_uuid"]
        first_events = get_recent_events(first_session, 100)

        core.close()
        shutdown_bean(ctx)
        ctx = start_bean(db_path=str(output / "core.sqlite"), silent=True)
        core = NativeReasoningService(output / "reasoning.sqlite")
        resumed_plan = GoalStateEngine().propose_plan(ctx["session_uuid"], "cognition-probe", templates)
        cycle = GoalCycle(actions, event_sink=event)
        recovered = cycle.recover_interrupted()
        completed = cycle.poll_due(max_goals=5)
        progress = cycle.plan_status("cognition-probe")
        runs = cycle.history()
        later_inputs = {"domain": "plan-ordering", "task_ref": "later", "query": "M2 N9 O4"}
        core.close()
        core = NativeReasoningService(output / "reasoning.sqlite")
        later = core.reason_local(**later_inputs)
        cold_later = cold.reason_local(**later_inputs)
        fixed_rule = "".join(k for k, _ in sorted(
            [("M", 2), ("N", 9), ("O", 4)], key=lambda pair: -pair[1]))
        no_replay = cycle.poll_due() == []
        source_root = Path(__file__).resolve().parents[2]
        source_paths = ["bean/cognition/goal_state.py", "bean/runtime/goal_cycle.py",
                        "bean/runtime/digital_experiment.py", "bean/evaluation/goal_plan_cycle.py"]
        report = {
            "schema": "bean.goal.plan.cognition_probe.v1", "synthetic_only": True,
            "plan_origin": "host_authored", "independent_world_truth_verified": False,
            "general_learning_advantage_proven": False, "model_weights_trained": False,
            "external_provider_calls": 0, "development_examples": len(examples),
            "observation_event_id": observed, "first_session": first_session,
            "resumed_session": ctx["session_uuid"], "first_progress": first_progress,
            "progress": progress, "recovered_interrupted": recovered,
            "continued_steps": len(completed), "no_replay": no_replay,
            "same_plan_ids": [p.proposal_id for p in plan] == [p.proposal_id for p in resumed_plan],
            "registered_actions": sorted(actions), "trace": trace, "runs": runs,
            "canonical_events": first_events + get_recent_events(ctx["session_uuid"], 100),
            "reasoning_journal": core.bank.journal.events(),
            "controls": {"cold_before": cold_before, "cold_later": cold_later,
                         "later_core": later, "fixed_rule_answer": fixed_rule,
                         "candidate_advantage_over_fixed_rule": 0 if later.get("answer") == fixed_rule else None},
            "source_files_sha256": {p: hashlib.sha256((source_root / p).read_bytes()).hexdigest()
                                    for p in source_paths},
            "elapsed_seconds": time.perf_counter() - started,
        }
    finally:
        core.close()
        cold.close()
        shutdown_bean(ctx)
    report["database_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in output.glob("*.sqlite")}
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    report["receipt_sha256"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New synthetic evidence directory")
    args = parser.parse_args()
    report = run_probe(args.output)
    print(json.dumps({"progress": report["progress"], "controls": report["controls"],
                      "receipt_sha256": report["receipt_sha256"]}, sort_keys=True))
    return 0 if report["progress"]["status"] == "completed" and report["no_replay"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

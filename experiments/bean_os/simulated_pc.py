#!/usr/bin/env python3
"""BEAN OS simulated PC: real BEAN reasoning, synthetic PC state, no hardware access.

Three registered simulated operations: clean temporary storage (-1), inspect/no-op
(0), and restart a stalled service (+1). The host provides measured results of
resettable interventions; it never supplies a policy to BEAN. BEAN learns a
bounded numeric hypothesis, persists its receipt, then acts from a reopened DB.
This is NOT a general computer-use agent or proof of hardware autonomy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from bean.learning.reasoning_service import NativeReasoningService

ACTIONS = {-1: "clean_temp", 0: "inspect", 1: "restart_service"}


def pc_case(case_id: str) -> dict:
    i = int(case_id)
    # Keep generated PC states within the same physical operating envelope
    # regardless of disjoint numeric IDs. Otherwise blind IDs in the 50,000s
    # turn supposedly healthy states into massive faults, changing the task.
    # The sensor vector still includes a unique per-case signal, so training,
    # validation and blind observations remain distinct.
    offset = ((i // 3) % 997) * 0.01
    kind = i % 3
    if kind == 0:
        disk, service = 85.0 + offset, 8.0 + offset
    elif kind == 1:
        disk, service = 8.0 + offset, 85.0 + offset
    else:
        disk = service = 8.0 + offset
    return {"disk_pressure": disk, "service_fault": service, "case": i}


def sensors(case_id: str) -> tuple[float, float, float]:
    pc = pc_case(case_id)
    return (round(pc["disk_pressure"] - 30, 6),
            round(pc["service_fault"] - 30, 6),
            round(pc["case"] * 0.0001, 6))


def penalty(pc: dict) -> float:
    return max(0.0, pc["disk_pressure"] - 30) + max(0.0, pc["service_fault"] - 30)


def simulate_action(case_id: str, action: int) -> dict:
    """Effect of one permitted action on an isolated copy of simulated state."""
    if action not in ACTIONS:
        raise ValueError("Unregistered simulated operation")
    before = pc_case(case_id)
    after = dict(before)
    cost = 0.0
    if action == -1:
        after["disk_pressure"] = max(0.0, after["disk_pressure"] - 70)
        cost = 3.0
    elif action == 1:
        after["service_fault"] = max(0.0, after["service_fault"] - 70)
        cost = 3.0
    return {"before": before, "after": after, "operation": ACTIONS[action],
            "reward": round(penalty(before) - penalty(after) - cost, 5)}


def reward(case_id: str, action: int) -> float:
    return simulate_action(case_id, action)["reward"]


def run(db_path: Path) -> dict:
    train = tuple(map(str, range(100, 160)))
    validate = tuple(map(str, range(1000, 1012)))
    blind = tuple(map(str, range(50000, 50060)))
    service = NativeReasoningService(db_path, model=None)
    try:
        discovery = service.discover_analogy(
            domain="bean_os_simulated_pc", task_ref="desktop-ops-v1",
            source_ref="simulated-pc:isolated-fixture-v1",
            probe_ids=train, validation_probe_ids=validate,
            observe=sensors, reward=reward, budget=12, method="disagreement",
            seed=42)
        receipt_id = discovery["receipt_id"]
    finally:
        service.close()

    # Reload the actual persisted BEAN hypothesis before scoring unseen cases.
    service = NativeReasoningService(db_path, model=None)
    try:
        cases = []
        for case_id in blind:
            decision = service.use_discovered_analogy(
                receipt_id=receipt_id, sensors=sensors(case_id))
            action = decision.get("action") if decision["status"] == "provisional_action" else None
            score_by_action = {str(a): reward(case_id, a) for a in ACTIONS}
            optimal = max(score_by_action.values())
            observation = simulate_action(case_id, action) if action is not None else None
            cases.append({
                "case_id": case_id, "decision": decision["status"],
                "action": ACTIONS.get(action), "reward": observation["reward"] if observation else None,
                "optimal_reward": optimal,
                "regret": round(optimal - observation["reward"], 5) if observation else None,
                "changed_simulated_state": observation["after"] if observation else None,
            })
    finally:
        service.close()
    attempts = [c for c in cases if c["reward"] is not None]
    success = sum(c["regret"] == 0 for c in attempts)
    result = {
        "schema": "bean.os.simulated_pc.v1",
        "simulation_only": True, "real_bean_core": True,
        "external_model_used": False, "hardware_access": False,
        "train_cases": len(train), "validation_cases": len(validate),
        "blind_cases": len(blind),
        "receipt_id": receipt_id, "journal_tip": discovery["journal_tip"],
        "learner_status": discovery["status"],
        "training_reward_calls": discovery["reward_calls"],
        "blind_actions_attempted": len(attempts),
        "blind_optimal_actions": success,
        "blind_optimal_rate": success / len(blind),
        "blind_coverage": len(attempts) / len(blind),
        "blind_mean_regret": (sum(c["regret"] for c in attempts) / len(attempts)
                              if attempts else None),
        "baseline_inspect_mean_reward": sum(reward(cid, 0) for cid in blind) / len(blind),
        "candidate_mean_reward": (sum(c["reward"] for c in attempts) / len(attempts)
                                  if attempts else None),
        "cases": cases,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="bean-pc-sim-") as tmp:
        result = run(Path(tmp) / "reasoning.sqlite3")
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    # Failure to learn is a measured result and should fail the acceptance gate.
    if result["blind_optimal_rate"] < 0.80 or result["blind_coverage"] < 0.80:
        raise SystemExit("BEAN simulated PC acceptance gate failed")


if __name__ == "__main__":
    main()

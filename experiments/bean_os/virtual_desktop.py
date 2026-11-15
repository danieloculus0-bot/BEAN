#!/usr/bin/env python3
"""BEAN OS virtual desktop experiment using BEAN's existing reasoning journal.

Five resettable simulated subsystems, each with two repairs and an inspect/no-op
choice. The native BEAN reasoner learns a policy using measured interventions,
reopens its actual persisted SQLite journal, then repeatedly inspects/acts on
unseen *multi-fault* desktop episodes. No LLM, shell, network, or real devices.

Scope: bounded numerical control learning, NOT free-form general computer use.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from bean.learning.reasoning_service import NativeReasoningService


# Registered simulation operations, NOT preselected decisions for any case.
OPERATIONS = {
    "storage": {-1: "purge_temporary_files", 1: "repair_write_permissions"},
    "services": {-1: "start_desktop_service", 1: "clear_service_deadlock"},
    "network": {-1: "restore_dns", 1: "renew_network_route"},
    "files": {-1: "restore_missing_document", 1: "repair_corrupt_document"},
    "apps": {-1: "launch_browser", 1: "reset_browser_profile"},
}
FAMILIES = tuple(OPERATIONS)
TRAIN = tuple(map(str, range(100, 160)))
VALIDATE = tuple(map(str, range(1000, 1012)))
BLIND = tuple(map(str, range(50000, 50060)))
EPISODES = 36


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class VirtualDesktop:
    """Disposable, observable PC state; never touches the host filesystem."""

    def __init__(self, conditions: dict[str, int], *, identity: int):
        if set(conditions) != set(FAMILIES) or any(
            type(v) is not int or v not in (-1, 0, 1)
            for v in conditions.values()
        ):
            raise ValueError("One bounded condition per simulated subsystem required")
        self.identity = identity
        self.state = {
            "storage": {
                "temp_files": ["cache.tmp", "outdated-download.tmp"]
                if conditions["storage"] == -1 else [],
                "writable": conditions["storage"] != 1,
            },
            "services": {
                "desktop_service": "stopped" if conditions["services"] == -1
                else "deadlocked" if conditions["services"] == 1 else "running",
            },
            "network": {
                "dns_ok": conditions["network"] != -1,
                "route_ok": conditions["network"] != 1,
            },
            "files": {
                "document_present": conditions["files"] != -1,
                "document_intact": conditions["files"] != 1,
                "backup_present": True,
            },
            "apps": {
                "browser_running": conditions["apps"] != -1,
                "profile_valid": conditions["apps"] != 1,
            },
        }
        self.history: list[dict] = []

    def _fault(self, family: str) -> int:
        d = self.state[family]
        if family == "storage":
            return -1 if d["temp_files"] else (1 if not d["writable"] else 0)
        if family == "services":
            return -1 if d["desktop_service"] == "stopped" else (
                1 if d["desktop_service"] == "deadlocked" else 0)
        if family == "network":
            return -1 if not d["dns_ok"] else (1 if not d["route_ok"] else 0)
        if family == "files":
            return -1 if not d["document_present"] else (
                1 if not d["document_intact"] else 0)
        if family == "apps":
            return -1 if not d["browser_running"] else (
                1 if not d["profile_valid"] else 0)
        raise ValueError("Unknown subsystem")

    def inspect(self, family: str) -> tuple[float, float, float]:
        """Return measured numeric channels only, not a fault label or oracle.

        A difference in two sensor signals encodes the physical observation;
        BEAN must discover whether a channel, difference, or constant policy
        predicts the best operation from measured intervention outcomes.
        """
        if family not in OPERATIONS:
            raise ValueError("Unknown subsystem")
        fault = self._fault(family)
        offset = ((self.identity // 3) % 719) * 0.007
        baseline = 12 + offset
        # Each family has a stable pair of comparable diagnostic counters.
        delta = fault * (4.5 + ((self.identity % 17) * 0.02))
        return (round(baseline + delta, 6), round(baseline, 6),
                round(self.identity * 0.001 + FAMILIES.index(family) * 0.00001, 6))

    def apply(self, family: str, choice: int) -> dict:
        """Execute a REGISTERED operation, independently measure improvement."""
        if family not in OPERATIONS or type(choice) is not int or choice not in (-1, 0, 1):
            raise ValueError("Operation not registered")
        previous = self._fault(family)
        operation = OPERATIONS[family].get(choice, "inspect_only")
        d = self.state[family]
        if choice == -1:
            if family == "storage":
                d["temp_files"] = []
            elif family == "services" and previous == -1:
                d["desktop_service"] = "running"
            elif family == "network":
                d["dns_ok"] = True
            elif family == "files":
                d["document_present"] = True
            elif family == "apps":
                d["browser_running"] = True
        elif choice == 1:
            if family == "storage":
                d["writable"] = True
            elif family == "services" and previous == 1:
                d["desktop_service"] = "running"
            elif family == "network":
                d["route_ok"] = True
            elif family == "files":
                d["document_intact"] = True
            elif family == "apps":
                d["profile_valid"] = True
        current = self._fault(family)
        improved = previous != 0 and current == 0
        wasted = choice != 0 and not improved
        result = {
            "family": family, "operation": operation,
            "choice": choice, "changed": improved, "unnecessary": wasted,
            "reward": 1.0 if improved else -0.25 if wasted else 0.0,
            "post_observation": self.inspect(family),
        }
        self.history.append(result)
        return result

    def complete(self) -> bool:
        return all(self._fault(family) == 0 for family in FAMILIES)

    def outstanding(self) -> int:
        """Evaluator-only result, not passed to BEAN's reasoning service."""
        return sum(self._fault(family) != 0 for family in FAMILIES)


def training_environment(family: str, case_id: str) -> VirtualDesktop:
    case = int(case_id)
    condition = (case % 3) - 1
    return VirtualDesktop({
        group: condition if group == family else 0 for group in FAMILIES
    }, identity=case)


def train(service: NativeReasoningService) -> dict[str, dict]:
    decisions = {}
    for family in FAMILIES:
        def observe(case_id: str, f=family):
            return training_environment(f, case_id).inspect(f)

        def reward(case_id: str, choice: int, f=family):
            return training_environment(f, case_id).apply(f, choice)["reward"]

        decisions[family] = service.discover_analogy(
            domain="bean_os_virtual_desktop", task_ref=f"desktop-repair:{family}",
            source_ref="simulated-pc:resettable-tools-v2",
            probe_ids=TRAIN, validation_probe_ids=VALIDATE,
            observe=observe, reward=reward, budget=12,
            # The current active disagreement sampler repeatedly selected
            # healthy probes for this telemetry layout and abstained on all
            # five learned policies. Use BEAN's native passive exploration
            # until its active selection receives a separately tested fix.
            method="passive", seed=42 + FAMILIES.index(family),
        )
    return decisions


def episode_conditions(index: int) -> dict[str, int]:
    """Predeclared blind episode cases; all tool results remain unexposed."""
    return {
        family: (0 if (index + i * 3) % 5 == 0
                 else (-1 if (index * 7 + i * 11) % 2 == 0 else 1))
        for i, family in enumerate(FAMILIES)
    }


def act_episode(service: NativeReasoningService, receipts: dict[str, str], index: int) -> dict:
    machine = VirtualDesktop(episode_conditions(index), identity=60000 + index)
    before = machine.outstanding()
    decisions = []
    for cycle in range(3):
        changed = False
        for family in FAMILIES:
            observation = machine.inspect(family)
            decision = service.use_discovered_analogy(
                receipt_id=receipts[family], sensors=observation)
            choice = decision.get("action") if decision["status"] == "provisional_action" else None
            if choice is None:
                decisions.append({"cycle": cycle, "family": family,
                                  "state": "abstain", "observation": observation})
                continue
            # Zero means the learned policy elects an inspection without repair.
            result = machine.apply(family, choice)
            changed = changed or result["changed"]
            decisions.append({"cycle": cycle, "family": family,
                              "state": "executed", "observation": observation,
                              **result})
        # Reinspection after every intervention; no infinite retries.
        if not changed:
            break
    actions = [d for d in decisions if d.get("choice") not in (None, 0)]
    return {
        "episode_id": index, "initial_faults": before,
        "remaining_faults": machine.outstanding(),
        "completed": machine.complete(),
        "repair_actions": len(actions),
        "unnecessary_actions": sum(d.get("unnecessary", False) for d in actions),
        "all_tools_simulated": True,
        "trace": decisions,
    }


def run(db_path: Path) -> dict:
    service = NativeReasoningService(db_path, model=None)
    try:
        learned = train(service)
        receipts = {f: learned[f]["receipt_id"] for f in FAMILIES}
        persisted_head = {f: learned[f]["journal_tip"] for f in FAMILIES}
    finally:
        service.close()

    # Reopen the existing BEAN Core journal so that a persisted, not in-memory,
    # hypothesis determines each action on blind multi-fault workstations.
    service = NativeReasoningService(db_path, model=None)
    try:
        episodes = [act_episode(service, receipts, index) for index in range(EPISODES)]
        for episode in episodes:
            trace = episode["trace"]
            evidence = {
                "schema": "bean.adaptive_lab026.v1",
                "experiment": "bean.os.virtual_desktop.v2",
                "episode_id": episode["episode_id"],
                "completed": episode["completed"],
                "initial_faults": episode["initial_faults"],
                "remaining_faults": episode["remaining_faults"],
                "actions": episode["repair_actions"],
                "unnecessary_actions": episode["unnecessary_actions"],
                "trace_sha256": sha256(canonical(trace).encode()).hexdigest(),
                "outcome_origin": "synthetic_resettable_host",
                "independently_authenticated": False,
                "external_model_used": False,
            }
            service.bank.record_trial(evidence)
        recorded = [
            row["data"] for row in service.bank.journal.events()
            if row["kind"] == "trial"
            and row["data"].get("experiment") == "bean.os.virtual_desktop.v2"
        ]
        if len(recorded) != len(episodes):
            raise ValueError("Missing persisted BEAN episode receipts")
        status = service.status()
    finally:
        service.close()

    completed = sum(e["completed"] for e in episodes)
    faults = sum(e["initial_faults"] for e in episodes)
    outstanding = sum(e["remaining_faults"] for e in episodes)
    actions = sum(e["repair_actions"] for e in episodes)
    unnecessary = sum(e["unnecessary_actions"] for e in episodes)
    return {
        "schema": "bean.os.virtual_desktop.v2",
        "simulation_only": True, "real_bean_core": True,
        "external_model_used": False, "physical_computer_connected": False,
        "training_environment_cases_per_family": len(TRAIN),
        "validation_cases_per_family": len(VALIDATE),
        "subsystems": list(FAMILIES), "learned_rules": len(learned),
        "accepted_rules": sum(v["status"] == "provisional_rule" for v in learned.values()),
        "policy_receipts": receipts, "training_journal_heads": persisted_head,
        "learning_diagnostics": {
            f: {"status": d["status"], "failure_reason": d["failure_reason"],
                "best_rule": d["best_rule"],
                "best_loss": d["best_loss_per_probe"],
                "runner_up_gap": d["second_best_gap_per_probe"],
                "probes": [
                    {"id": row["probe_id"],
                     "sensors": row["sensors"]}
                    for row in d["records"]
                ],
                "validated": d["validation"]["passed"]}
            for f, d in learned.items()
        },
        "persisted_episode_records": len(recorded),
        "blind_episodes": len(episodes),
        "completed_episodes": completed,
        "completion_rate": completed / len(episodes),
        "initial_faults": faults,
        "remaining_faults": outstanding,
        "fault_repair_rate": (faults - outstanding) / faults if faults else None,
        "repair_actions": actions,
        "unnecessary_actions": unnecessary,
        "unnecessary_action_rate": unnecessary / actions if actions else 0.0,
        "memory_status": status,
        "episodes": episodes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="bean-virtual-desktop-") as folder:
        result = run(Path(folder) / "bean_reasoning.sqlite3")
    report = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
    if (result["completion_rate"] < 0.80
        or result["unnecessary_action_rate"] > 0.10
        or result["persisted_episode_records"] != EPISODES):
        raise SystemExit("BEAN virtual desktop acceptance gate failed")


if __name__ == "__main__":
    main()

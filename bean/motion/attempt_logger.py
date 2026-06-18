"""
bean/motion/attempt_logger.py

Writes every movement attempt into the BEAN memory core.
Uses the event_logger — not a direct DB write.

An "attempt" is any time BEAN tries to execute a motion command or sequence,
whether it was safe, unsafe, simulated, or real.

All outcomes are logged:
  - REJECTED_BY_SAFETY: command failed safety check
  - SIMULATED_SUCCESS:  command passed safety and simulator accepted it
  - SIMULATED_FAILURE:  command passed safety but simulator reported an issue
  - SKIPPED_NO_HARDWARE: command passed safety but hardware not connected
  - TEACHING_RECORD:    command recorded during a teaching session

Nothing in this file makes decisions. It only records.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ..memory.event_logger import log_event, EventType, Source, Severity


class AttemptOutcome(str, Enum):
    REJECTED_BY_SAFETY   = "rejected_by_safety"
    SIMULATED_SUCCESS    = "simulated_success"
    SIMULATED_FAILURE    = "simulated_failure"
    SKIPPED_NO_HARDWARE  = "skipped_no_hardware"
    TEACHING_RECORD      = "teaching_record"


def log_command_attempt(
    session_uuid: str,
    command,                         # MotionCommand
    outcome: AttemptOutcome,
    violations: Optional[list[str]] = None,
    resolved_target: Optional[float] = None,
    simulator_notes: Optional[str] = None,
    skill_name: Optional[str] = None,
) -> int:
    """
    Log a single command attempt to memory.
    Returns the event id.
    """
    severity = (
        Severity.WARN if outcome == AttemptOutcome.REJECTED_BY_SAFETY
        else Severity.INFO
    )

    summary = _build_summary(command, outcome, skill_name)

    data = {
        "command": command.to_dict(),
        "outcome": outcome.value,
        "resolved_target": resolved_target,
        "violations": violations or [],
        "simulator_notes": simulator_notes,
        "skill_name": skill_name,
    }

    return log_event(
        session_uuid=session_uuid,
        event_type=EventType.BODY_STATE,
        subtype=f"motion_attempt:{outcome.value}",
        summary=summary,
        source=Source.SYSTEM,
        data=data,
        severity=severity,
    )


def log_sequence_attempt(
    session_uuid: str,
    sequence,                         # MotionSequence
    verdicts: list,                   # list[SafetyVerdict]
    outcomes: list[AttemptOutcome],
    skill_name: Optional[str] = None,
    teaching: bool = False,
) -> int:
    """
    Log a full sequence attempt as a single memory event.
    Returns the event id.
    """
    total = len(sequence.commands)
    approved_count = sum(1 for v in verdicts if v.approved)
    failed_count = total - approved_count

    all_passed = approved_count == total
    severity = Severity.INFO if all_passed else Severity.WARN

    action = "teaching record" if teaching else "sequence attempt"
    summary = (
        f"Motion {action}: '{sequence.name}' — "
        f"{approved_count}/{total} steps approved"
        + (f", {failed_count} rejected" if failed_count else "")
    )

    data = {
        "sequence_name": sequence.name,
        "sequence_id": sequence.sequence_id,
        "skill_name": skill_name,
        "teaching": teaching,
        "total_steps": total,
        "approved_steps": approved_count,
        "failed_steps": failed_count,
        "all_passed": all_passed,
        "steps": [
            {
                "command_id": v.command.command_id,
                "joint_id": v.command.joint_id,
                "intent": v.command.intent.value,
                "target_pos": v.command.target_pos,
                "resolved_target": v.resolved_target,
                "approved": v.approved,
                "violations": v.violations,
                "outcome": outcomes[i].value if i < len(outcomes) else "unknown",
            }
            for i, v in enumerate(verdicts)
        ],
    }

    return log_event(
        session_uuid=session_uuid,
        event_type=EventType.BODY_STATE,
        subtype=f"motion_sequence:{'teaching' if teaching else 'replay'}",
        summary=summary,
        source=Source.SYSTEM,
        data=data,
        severity=severity,
    )


def log_safety_rejection(
    session_uuid: str,
    command,
    violations: list[str],
) -> int:
    """
    Log a safety rejection. Slightly higher visibility than a normal attempt.
    """
    summary = (
        f"SAFETY REJECTED: joint='{command.joint_id}' "
        f"intent='{command.intent.value}' "
        f"target={command.target_pos} — {violations[0] if violations else 'unknown'}"
    )
    return log_event(
        session_uuid=session_uuid,
        event_type=EventType.SAFETY_TRIGGER,
        subtype="motion_safety_rejection",
        summary=summary,
        source=Source.SAFETY,
        data={
            "command": command.to_dict(),
            "violations": violations,
        },
        severity=Severity.WARN,
    )

def _build_summary(command, outcome: AttemptOutcome, skill_name: Optional[str]) -> str:
    skill_part = f" [skill: {skill_name}]" if skill_name else ""
    return (
        f"Motion attempt{skill_part}: joint='{command.joint_id}' "
        f"intent='{command.intent.value}' "
        f"target={command.target_pos} speed={command.speed} "
        f"→ {outcome.value}"
    )

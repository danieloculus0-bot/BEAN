"""
bean/motion/safety.py

The motion safety layer. Every command passes through here.
No exceptions. No bypasses. No "just this once."

The safety layer consults the body registry for limits,
validates the command, and returns a structured verdict.

A SafetyVerdict carries:
  - approved: bool
  - violations: list of what was wrong
  - adjusted_command: None (we do not silently adjust - we reject and explain)

Design principle: we do not silently clamp commands to safe values.
Silent clamping hides bugs and erodes trust in the command chain.
If a command is out of range, it is REJECTED with a clear reason.
The caller must fix the command and resubmit.

The one exception: NEUTRAL intent. For NEUTRAL commands, we resolve
the target_pos from the registry and validate that. This is intentional
because neutral is always known and safe.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from ..body.registry import get_registry, BodyRegistry
from .command import MotionCommand, CommandIntent


@dataclass
class SafetyVerdict:
    """
    The result of a safety check on one MotionCommand.

    approved   : True only if ALL checks passed
    violations : list of human-readable violation strings (empty if approved)
    command    : the command that was checked (unchanged)
    resolved_target: the actual target position used for validation
                      (matters for NEUTRAL/MOVE_BY intents)
    """
    approved: bool
    violations: list[str]
    command: MotionCommand
    resolved_target: Optional[float] = None

    def summary(self) -> str:
        if self.approved:
            return f"APPROVED: {self.command.joint_id} → {self.resolved_target}"
        return (
            f"REJECTED: {self.command.joint_id} "
            f"[{'; '.join(self.violations)}]"
        )


class MotionSafety:
    """
    Validates motion commands against the body registry.

    One instance per session. Stateless between calls
    (the registry holds all the state we need).
    """

    def __init__(self, registry: Optional[BodyRegistry] = None):
        self._registry = registry or get_registry()

    def check(
        self,
        command: MotionCommand,
        current_pos: Optional[float] = None,
    ) -> SafetyVerdict:
        """
        Validate one MotionCommand.

        current_pos: current joint position (needed for MOVE_BY resolution).
                     If None and intent is MOVE_BY, that is itself a violation.

        Returns SafetyVerdict. Never raises. Never moves anything.
        """
        violations: list[str] = []

        # 1. Joint must exist in registry
        if not self._registry.joint_exists(command.joint_id):
            return SafetyVerdict(
                approved=False,
                violations=[f"UNKNOWN_JOINT: '{command.joint_id}' not in body registry"],
                command=command,
                resolved_target=None,
            )

        joint_def = self._registry.get_joint(command.joint_id)
        limits = joint_def.limits

        # 2. Resolve target position based on intent
        resolved_target: Optional[float] = None

        if command.intent == CommandIntent.NEUTRAL:
            resolved_target = joint_def.neutral_pos

        elif command.intent == CommandIntent.MOVE_TO:
            resolved_target = command.target_pos

        elif command.intent == CommandIntent.MOVE_BY:
            if current_pos is None:
                violations.append(
                    "MOVE_BY_WITHOUT_CURRENT_POS: cannot resolve delta without "
                    "current position. Pass current_pos to safety.check()."
                )
                return SafetyVerdict(
                    approved=False,
                    violations=violations,
                    command=command,
                    resolved_target=None,
                )
            resolved_target = current_pos + command.target_pos

        elif command.intent == CommandIntent.HOLD:
            # HOLD uses current position — no movement, just validate speed
            resolved_target = current_pos if current_pos is not None else joint_def.neutral_pos

        else:
            violations.append(f"UNKNOWN_INTENT: '{command.intent}'")
            return SafetyVerdict(
                approved=False,
                violations=violations,
                command=command,
                resolved_target=None,
            )

        # 3. Run limit validation
        limit_violations = limits.validate(resolved_target, command.speed)
        violations.extend(limit_violations)

        # 4. Hardware not connected is NOT a safety violation —
        #    but we annotate the verdict so the simulator knows.
        #    (The simulator will handle this separately.)

        return SafetyVerdict(
            approved=len(violations) == 0,
            violations=violations,
            command=command,
            resolved_target=resolved_target,
        )

    def check_sequence(
        self,
        sequence,
        current_positions: Optional[dict[str, float]] = None,
    ) -> list[SafetyVerdict]:
        """
        Validate every command in a MotionSequence.
        Returns one SafetyVerdict per command.
        Short-circuits on the first failure: remaining commands are not checked.

        This means: if step 2 of 5 fails, you get verdicts for steps 1 and 2 only.
        The caller must fix step 2 before proceeding.
        """
        verdicts: list[SafetyVerdict] = []
        current_pos_map = dict(current_positions or {})

        for cmd in sequence.commands:
            current = current_pos_map.get(cmd.joint_id)
            verdict = self.check(cmd, current_pos=current)
            verdicts.append(verdict)

            if not verdict.approved:
                break  # stop at first failure

            # Update our local position tracker for MOVE_BY resolution
            if verdict.resolved_target is not None:
                current_pos_map[cmd.joint_id] = verdict.resolved_target

        return verdicts

    def all_approved(self, verdicts: list[SafetyVerdict]) -> bool:
        """True only if every verdict in the list is approved."""
        return len(verdicts) > 0 and all(v.approved for v in verdicts)

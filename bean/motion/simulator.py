"""
bean/motion/simulator.py

The motion simulator. Accepts safety-approved commands.
Returns simulated body state changes. Updates BodyState.

The simulator is not pretend hardware. It is a stand-in execution layer
that lets BEAN practice movement logic, teaching, and skill replay
before hardware is wired.

The simulator is honest about what it is:
  - It does not verify that the joint actually moved.
  - It does not produce sensor feedback.
  - It updates BodyState with ESTIMATED positions only.
  - It logs every execution honestly as simulated.

When real hardware drivers exist, they replace the simulator's
execution step. Everything above (safety, skills, teaching) stays the same.

The simulator WILL refuse to run commands that:
  - Did not pass through the safety layer (no SafetyVerdict = no execution)
  - Have approved=False verdicts
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from ..body.state import BodyState
from .command import MotionCommand, MotionSequence, CommandIntent
from .safety import SafetyVerdict
from .attempt_logger import (
    AttemptOutcome,
    log_command_attempt,
    log_sequence_attempt,
)


@dataclass
class SimulatorResult:
    """Result of one simulated command execution."""
    success: bool
    command: MotionCommand
    verdict: SafetyVerdict
    outcome: AttemptOutcome
    new_position: Optional[float] = None
    notes: str = ""


class MotionSimulator:
    """
    Simulates command execution. Updates BodyState. Logs attempts.

    Does not execute on real hardware.
    Does not accept unapproved commands.
    """

    def __init__(self, body_state: BodyState):
        self._body_state = body_state

    def execute(
        self,
        command: MotionCommand,
        verdict: SafetyVerdict,
        session_uuid: Optional[str] = None,
        skill_name: Optional[str] = None,
    ) -> SimulatorResult:
        """
        Execute one safety-approved command in simulation.

        Requires a SafetyVerdict with approved=True.
        If verdict is not approved, returns failure without executing.
        """
        if not verdict.approved:
            outcome = AttemptOutcome.REJECTED_BY_SAFETY
            if session_uuid:
                log_command_attempt(
                    session_uuid=session_uuid,
                    command=command,
                    outcome=outcome,
                    violations=verdict.violations,
                    skill_name=skill_name,
                )
            return SimulatorResult(
                success=False,
                command=command,
                verdict=verdict,
                outcome=outcome,
                notes=f"Rejected: {'; '.join(verdict.violations)}",
            )

        # Check hardware connection status
        from ..body.registry import get_registry
        registry = get_registry()
        joint_def = registry.get_joint(command.joint_id)

        if not joint_def.hardware_connected:
            # Safe command, but no hardware. Simulate and note it.
            outcome = AttemptOutcome.SIMULATED_SUCCESS
            new_pos = verdict.resolved_target
            notes = f"Simulated (hardware not connected): {command.joint_id} → {new_pos}"
        else:
            # Hardware is connected. In this layer we still only simulate.
            # The real hardware driver replaces this path.
            outcome = AttemptOutcome.SIMULATED_SUCCESS
            new_pos = verdict.resolved_target
            notes = f"Simulated (hardware connected but driver not active): {command.joint_id} → {new_pos}"

        # Update body state
        if new_pos is not None:
            self._body_state.apply_simulated_result(command.joint_id, new_pos)

        if session_uuid:
            log_command_attempt(
                session_uuid=session_uuid,
                command=command,
                outcome=outcome,
                resolved_target=new_pos,
                simulator_notes=notes,
                skill_name=skill_name,
            )

        return SimulatorResult(
            success=True,
            command=command,
            verdict=verdict,
            outcome=outcome,
            new_position=new_pos,
            notes=notes,
        )

    def execute_sequence(
        self,
        sequence: MotionSequence,
        verdicts: list[SafetyVerdict],
        session_uuid: Optional[str] = None,
        skill_name: Optional[str] = None,
        teaching: bool = False,
    ) -> list[SimulatorResult]:
        """
        Execute a full sequence of safety-approved commands.

        Stops at the first failure.
        Logs the full sequence as one memory event after completion.
        """
        if len(verdicts) != len(sequence.commands):
            raise ValueError(
                f"Verdict count ({len(verdicts)}) must match "
                f"command count ({len(sequence.commands)})"
            )

        results: list[SimulatorResult] = []
        outcomes: list[AttemptOutcome] = []

        for cmd, verdict in zip(sequence.commands, verdicts):
            result = self.execute(
                command=cmd,
                verdict=verdict,
                session_uuid=None,  # log individually below via sequence log
                skill_name=skill_name,
            )
            results.append(result)
            outcomes.append(result.outcome)

            if not result.success:
                break  # stop at first failure

        # Log the whole sequence as one event
        if session_uuid:
            executed_verdicts = verdicts[: len(results)]
            log_sequence_attempt(
                session_uuid=session_uuid,
                sequence=sequence,
                verdicts=executed_verdicts,
                outcomes=outcomes,
                skill_name=skill_name,
                teaching=teaching,
            )

        return results

    def current_positions(self) -> dict[str, float]:
        """Return current simulated positions for all joints."""
        return {
            s.joint_id: s.position
            for s in self._body_state._state_map.all_states()
        }

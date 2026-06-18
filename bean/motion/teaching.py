"""
bean/motion/teaching.py

Teaching layer for supervised movement capture and replay.
This is where demonstrations become named skills.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .command import MotionCommand, MotionSequence, CommandSource
from .safety import MotionSafety, SafetyVerdict
from .simulator import MotionSimulator
from .attempt_logger import AttemptOutcome, log_command_attempt, log_safety_rejection
from .skills import Skill, SkillLibrary


@dataclass
class TeachingSession:
    name: str
    taught_by: str
    accepted_commands: list[MotionCommand] = field(default_factory=list)
    rejected_verdicts: list[SafetyVerdict] = field(default_factory=list)


class TeachingLayer:
    def __init__(self, safety: MotionSafety, simulator: MotionSimulator, library: SkillLibrary, body_state):
        self.safety = safety
        self.simulator = simulator
        self.library = library
        self.body_state = body_state
        self._active: Optional[TeachingSession] = None

    def begin_teaching(self, name: str, taught_by: str = "supervisor", session_uuid: Optional[str] = None):
        if self._active is not None:
            raise RuntimeError("A teaching session is already active.")
        self._active = TeachingSession(name=name, taught_by=taught_by)

    def teach_command(self, command: MotionCommand, session_uuid: Optional[str] = None) -> SafetyVerdict:
        if self._active is None:
            raise RuntimeError("No active teaching session. Call begin_teaching() first.")
        current = self.body_state.get_joint(command.joint_id).position if command.joint_id else None
        verdict = self.safety.check(command, current_pos=current)
        if verdict.approved:
            self._active.accepted_commands.append(command)
            if session_uuid:
                log_command_attempt(session_uuid, command, AttemptOutcome.TEACHING_RECORD, resolved_target=verdict.resolved_target, skill_name=self._active.name)
        else:
            self._active.rejected_verdicts.append(verdict)
            if session_uuid:
                log_command_attempt(session_uuid, command, AttemptOutcome.REJECTED_BY_SAFETY, violations=verdict.violations, skill_name=self._active.name)
                log_safety_rejection(session_uuid, command, verdict.violations)
        return verdict

    def commit_teaching(self, description: str = "Taught movement skill.", session_uuid: Optional[str] = None) -> Optional[Skill]:
        if self._active is None:
            raise RuntimeError("No active teaching session to commit.")
        active = self._active
        self._active = None
        if not active.accepted_commands:
            return None
        sequence = MotionSequence(
            name=active.name,
            commands=list(active.accepted_commands),
            source=CommandSource.TEACHER,
            notes="Captured from supervised teaching session.",
        )
        skill = Skill(
            name=active.name,
            description=description,
            body_parts=sequence.joints_used(),
            sequence=sequence,
            preconditions=["Supervisor taught or approved this motion."],
            safety_notes="Replay only through MotionSafety and simulator/hardware driver.",
            taught_by=active.taught_by,
        )
        existing = self.library.load(active.name)
        if existing:
            skill.skill_uuid = existing.skill_uuid
            skill.created_at = existing.created_at
            skill.reset_learning()
        self.library.save(skill)
        return skill

    def abandon_teaching(self, session_uuid: Optional[str] = None):
        self._active = None

    def replay_skill(self, name: str, session_uuid: Optional[str] = None) -> dict:
        skill = self.library.load(name)
        if skill is None:
            return {"success": False, "reason": f"Skill not found: {name}"}
        if len(skill.sequence.commands) == 0:
            skill.record_attempt(False)
            self.library.save(skill)
            return {"success": False, "reason": "Skill is a stub or empty command sequence.", "new_confidence": skill.confidence}
        current_positions = self.simulator.current_positions()
        verdicts = self.safety.check_sequence(skill.sequence, current_positions=current_positions)
        if len(verdicts) != len(skill.sequence.commands) or not self.safety.all_approved(verdicts):
            skill.record_attempt(False)
            self.library.save(skill)
            if session_uuid and verdicts:
                bad = verdicts[-1]
                log_command_attempt(session_uuid, bad.command, AttemptOutcome.REJECTED_BY_SAFETY, violations=bad.violations, skill_name=name)
            return {"success": False, "reason": "Safety check failed during replay.", "new_confidence": skill.confidence}
        results = self.simulator.execute_sequence(skill.sequence, verdicts, session_uuid=session_uuid, skill_name=name)
        success = len(results) == len(skill.sequence.commands) and all(r.success for r in results)
        skill.record_attempt(success)
        self.library.save(skill)
        return {"success": success, "reason": "ok" if success else "Replay failed.", "new_confidence": skill.confidence}

"""
bean/motion/command.py

Motion command objects. The vocabulary of movement.

A MotionCommand is a structured intent to move one joint to one position
at one speed. It is not an instruction to hardware. It is a request
that must pass through the safety layer before anything happens.

A MotionSequence is an ordered list of MotionCommands with optional
inter-step delays. This is what skills are made of.

Rules:
  - Commands are immutable after creation.
  - Commands carry their own source annotation (who asked for this move).
  - Commands do NOT reference hardware channels directly - they use joint_id.
    The hardware driver (future layer) resolves joint_id to channel.
  - Nothing in this file sends anything to hardware.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CommandSource(str, Enum):
    TEACHER      = "teacher"      # supervisor demonstrating a movement
    SKILL_REPLAY = "skill_replay" # replaying a learned skill
    SYSTEM       = "system"       # internal system (e.g. reset to neutral)
    TEST         = "test"         # test harness only


class CommandIntent(str, Enum):
    MOVE_TO      = "move_to"      # move joint to absolute position
    MOVE_BY      = "move_by"      # move joint by relative delta
    HOLD         = "hold"         # hold current position for duration
    NEUTRAL      = "neutral"      # return joint to neutral position


@dataclass(frozen=True)
class MotionCommand:
    """
    A single joint motion command.

    joint_id    : which joint to move (looked up in body registry)
    intent      : what kind of move
    target_pos  : target position (degrees or PWM units)
                  For MOVE_BY: this is a delta. For HOLD/NEUTRAL: ignored.
    speed       : movement speed (units/second). Must be > 0.
    duration_ms: optional hold duration for HOLD intent
    source      : who generated this command
    command_id  : unique ID for audit trail
    created_at  : when the command was created
    notes       : free text - why this command was generated
    """
    joint_id:    str
    intent:      CommandIntent
    target_pos:  float
    speed:       float
    source:      CommandSource = CommandSource.SYSTEM
    duration_ms: Optional[int] = None
    notes:       str = ""
    command_id:  str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:  str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "command_id": self.command_id,
            "joint_id": self.joint_id,
            "intent": self.intent.value,
            "target_pos": self.target_pos,
            "speed": self.speed,
            "source": self.source.value,
            "duration_ms": self.duration_ms,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def move_to(cls, joint_id: str, target_pos: float, speed: float,
                source: CommandSource = CommandSource.SYSTEM,
                notes: str = "") -> "MotionCommand":
        return cls(
            joint_id=joint_id,
            intent=CommandIntent.MOVE_TO,
            target_pos=target_pos,
            speed=speed,
            source=source,
            notes=notes,
        )

    @classmethod
    def neutral(cls, joint_id: str,
                source: CommandSource = CommandSource.SYSTEM,
                notes: str = "") -> "MotionCommand":
        return cls(
            joint_id=joint_id,
            intent=CommandIntent.NEUTRAL,
            target_pos=0.0,  # ignored by safety layer for NEUTRAL intent
            speed=10.0,      # slow and safe for neutral returns
            source=source,
            notes=notes or "Return to neutral.",
        )


@dataclass
class MotionSequence:
    """
    An ordered list of MotionCommands with optional inter-step delays.
    This is the unit that skills store and replay.

    step_delay_ms: milliseconds to wait between steps during replay.
                   Actual timing is handled by the simulator or hardware driver.
    """
    name: str
    commands: list[MotionCommand]
    step_delay_ms: int = 200
    source: CommandSource = CommandSource.SYSTEM
    sequence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: str = ""

    def __len__(self) -> int:
        return len(self.commands)

    def joints_used(self) -> list[str]:
        """Return unique list of joint_ids in this sequence."""
        seen = []
        for cmd in self.commands:
            if cmd.joint_id not in seen:
                seen.append(cmd.joint_id)
        return seen 

    def to_dict(self) -> dict:
        return {
            "sequence_id": self.sequence_id,
            "name": self.name,
            "step_delay_ms": self.step_delay_ms,
            "source": self.source.value,
            "command_count": len(self.commands),
            "joints_used": self.joints_used(),
            "commands": [c.to_dict() for c in self.commands],
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MotionSequence":
        commands = [
            MotionCommand(
                joint_id=c["joint_id"],
                intent=CommandIntent(c["intent"]),
                target_pos=c["target_pos"],
                speed=c["speed"],
                source=CommandSource(c["source"]),
                duration_ms=c.get("duration_ms"),
                notes=c.get("notes", ""),
                command_id=c.get("command_id", str(uuid.uuid4())),
                created_at=c.get("created_at", datetime.now(timezone.utc).isoformat()),
            )
            for c in d["commands"]
        ]
        return cls(
            name=d["name"],
            commands=commands,
            step_delay_ms=d.get("step_delay_ms", 200),
            source=CommandSource(d.get("source", "system")),
            sequence_id=d.get("sequence_id", str(uuid.uuid4())),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            notes=d.get("notes", ""),
        )

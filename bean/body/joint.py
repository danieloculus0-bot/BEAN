"""
bean/body/joint.py

Runtime state of a single joint.
Separate from JointDefinition (which is static config).
JointState tracks where the joint actually is (or is believed to be)
during a session.

In the absence of real hardware feedback, the state is the last
commanded position. This is explicitly tracked as "estimated" not
"confirmed." The distinction matters and is not papered over.

Nothing here sends commands. Nothing here talks to servos.
This is a stateful record only.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class JointStateKind(str, Enum):
    UNKNOWN    = "unknown"     # no information yet
    NEUTRAL    = "neutral"     # known to be at neutral_pos
    ESTIMATED  = "estimated"   # last commanded position, not confirmed by sensor
    CONFIRMED  = "confirmed"   # confirmed by sensor feedback (future capability)
    FAULT      = "fault"       # known error state


@dataclass
class JointState:
    """
    Current runtime state of one joint.

    position:  where the joint is or is estimated to be
    kind:      how reliable this position estimate is
    timestamp: when this state was last updated
    notes:     any anomaly or context worth logging
    """
    joint_id: str
    position: float
    kind: JointStateKind = JointStateKind.UNKNOWN
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: str = ""

    def update(self, new_pos: float, kind: JointStateKind, notes: str = ""):
        self.position = new_pos
        self.kind = kind
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "joint_id": self.joint_id,
            "position": self.position,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


class BodyStateMap:
    """
    Runtime state of all joints in the body.
    Initialized from the registry at boot.
    Updated by the simulator (or real hardware driver when that exists).
    """

    def __init__(self):
        self._states: dict[str, JointState] = {}

    def initialize_from_registry(self, registry) -> "BodyStateMap":
        """
        Set all joints to their neutral positions.
        Kind = NEUTRAL because we assume BEAN starts in neutral.
        This assumption should be validated on real hardware eventually.
        """
        for joint in registry.all_joints():
            self._states[joint.joint_id] = JointState(
                joint_id=joint.joint_id,
                position=joint.neutral_pos,
                kind=JointStateKind.NEUTRAL,
                notes="Initialized from registry neutral position.",
            )
        return self

    def get(self, joint_id: str) -> JointState:
        if joint_id not in self._states:
            raise KeyError(f"No state for joint '{joint_id}'")
        return self._states[joint_id]

    def update(self, joint_id: str, position: float,
               kind: JointStateKind = JointStateKind.ESTIMATED,
               notes: str = ""):
        if joint_id not in self._states:
            self._states[joint_id] = JointState(
                joint_id=joint_id,
                position=position,
                kind=kind,
                notes=notes,
            )
        else:
            self._states[joint_id].update(position, kind, notes)

    def snapshot(self) -> dict:
        """Return current state of all joints as a serializable dict."""
        return {jid: s.to_dict() for jid, s in self._states.items()}

    def all_states(self) -> list[JointState]:
        return list(self._states.values())

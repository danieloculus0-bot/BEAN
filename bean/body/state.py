"""
bean/body/state.py

Session-level body state manager.
Combines the static body registry with the runtime joint state map.

This is what the rest of BEAN talks to when it wants to know:
  - Where is the left elbow right now?
  - What joints make up the left arm?
  - Is joint X at neutral?

Also writes body state snapshots into BEAN's memory core
when requested (e.g. at session start, after motion events).

Does not command anything. Does not talk to hardware.
Is the authoritative answer to "where is BEAN's body right now?"
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional

from .registry import BodyRegistry, get_registry
from .joint import BodyStateMap, JointState, JointStateKind


class BodyState:
    """
    Runtime body state for one session.
    Initialized at session boot from the registry.
    """

    def __init__(self, registry: Optional[BodyRegistry] = None):
        self._registry = registry or get_registry()
        self._state_map = BodyStateMap()
        self._state_map.initialize_from_registry(self._registry)
        self._initialized_at = datetime.now(timezone.utc).isoformat()

    # ── Queries ──────────────────────────────────────────────────────

    def get_joint(self, joint_id: str) -> JointState:
        return self._state_map.get(joint_id)

    def get_limb_states(self, limb_id: str) -> dict[str, JointState]:
        joints = self._registry.joints_for_limb(limb_id)
        return {j.joint_id: self._state_map.get(j.joint_id) for j in joints}

    def is_at_neutral(self, joint_id: str) -> bool:
        joint_def = self._registry.get_joint(joint_id)
        state = self._state_map.get(joint_id)
        return abs(state.position - joint_def.neutral_pos) < 0.5

    def snapshot(self) -> dict:
        return {
            "initialized_at": self._initialized_at,
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
            "joints": self._state_map.snapshot(),
        }

    # ── Updates ──────────────────────────────────────────────────────

    def apply_simulated_result(self, joint_id: str, new_position: float):
        """
        Update joint state after a successful simulated command.
        Kind = ESTIMATED because we have no sensor confirmation.
        """
        self._state_map.update(
            joint_id=joint_id,
            position=new_position,
            kind=JointStateKind.ESTIMATED,
            notes="Updated by simulator after safe command.",
        )

    def reset_to_neutral(self, joint_id: Optional[str] = None):
        """
        Reset one joint (or all joints) to neutral position.
        Used at session start or after fault recovery.
        """
        if joint_id:
            joint_def = self._registry.get_joint(joint_id)
            self._state_map.update(
                joint_id=joint_id,
                position=joint_def.neutral_pos,
                kind=JointStateKind.NEUTRAL,
                notes="Reset to neutral by BodyState.reset_to_neutral().",
            )
        else:
            for joint_def in self._registry.all_joints():
                self._state_map.update(
                    joint_id=joint_def.joint_id,
                    position=joint_def.neutral_pos,
                    kind=JointStateKind.NEUTRAL,
                    notes="Reset to neutral (full body reset).",
                )

    def write_to_memory(self, session_uuid: str):
        """
        Write a body state snapshot into BEAN's memory core.
        Uses the event logger - not a direct DB write.
        """
        from ..memory.event_logger import log_event, EventType, Source
        snapshot = self.snapshot()
        log_event(
            session_uuid=session_uuid,
            event_type=EventType.BODY_STATE,
            summary="Body state snapshot recorded.",
            source=Source.SYSTEM,
            data=snapshot,
        )

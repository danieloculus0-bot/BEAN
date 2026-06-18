"""
bean/body/registry.py

The body registry. Defines BEAN's physical structure: limbs, joints,
servos, neutral positions, limits, safe ranges, and forbidden ranges.

This is the single source of truth about what BEAN's body looks like.
The safety layer consults this before permitting any motion command.

The registry is loaded from a JSON config file (body_registry.json),
not hardcoded here. This file defines the data model and loader only.

Nothing in this file moves anything. It describes. That's it.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .limits import JointLimits, ForbiddenRange


@dataclass
class JointDefinition:
    """
    One joint (or servo channel) in BEAN's body.

    Fields:
        joint_id    : unique string, e.g. "left_elbow"
        label       : human-readable name
        servo_channel: physical channel index (None = not yet wired)
        neutral_pos : safe resting position (degrees or PWM units)
        limits      : min/max/speed/safe_range/forbidden_ranges
        notes       : free-text; why this joint exists, caveats
        hardware_connected: False until explicitly confirmed and logged
    """
    joint_id: str
    label: str
    servo_channel: Optional[int]
    neutral_pos: float
    limits: JointLimits
    notes: str = ""
    hardware_connected: bool = False

    def to_dict(self) -> dict:
        return {
            "joint_id": self.joint_id,
            "label": self.label,
            "servo_channel": self.servo_channel,
            "neutral_pos": self.neutral_pos,
            "limits": self.limits.to_dict(),
            "notes": self.notes,
            "hardware_connected": self.hardware_connected,
        }


@dataclass
class LimbDefinition:
    """
    A named limb: a logical grouping of joints.
    e.g. "left_arm" contains "left_shoulder", "left_elbow", "left_wrist"
    """
    limb_id: str
    label: str
    joint_ids: list[str]
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "limb_id": self.limb_id,
            "label": self.label,
            "joint_ids": self.joint_ids,
            "notes": self.notes,
        }


class BodyRegistry:
    """
    The complete map of BEAN's physical body.

    Loaded from a JSON config. Provides lookup by joint_id or limb_id.
    Does not move anything. Does not talk to hardware.
    """

    def __init__(self):
        self._joints: dict[str, JointDefinition] = {}
        self._limbs: dict[str, LimbDefinition] = {}
        self._loaded_from: Optional[str] = None

    # ── Loading ──────────────────────────────────────────────────────

    def load(self, config_path: str) -> "BodyRegistry":
        """
        Load body definition from a JSON config file.
        Returns self for chaining.
        Raises ValueError if the config is invalid or missing required fields.
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Body config not found: {config_path}")

        raw = json.loads(path.read_text())
        self._load_from_dict(raw)
        self._loaded_from = str(path)
        return self

    def load_from_dict(self, raw: dict) -> "BodyRegistry":
        """Load from a dict directly (useful for tests)."""
        self._load_from_dict(raw)
        return self

    def _load_from_dict(self, raw: dict):
        self._joints.clear()
        self._limbs.clear()

        for jd in raw.get("joints", []):
            limits_raw = jd.get("limits", {})
            forbidden = [
                ForbiddenRange(fr["min_pos"], fr["max_pos"], fr.get("reason", ""))
                for fr in limits_raw.get("forbidden_ranges", [])
            ]
            limits = JointLimits(
                min_pos=limits_raw["min_pos"],
                max_pos=limits_raw["max_pos"],
                safe_min=limits_raw.get("safe_min", limits_raw["min_pos"]),
                safe_max=limits_raw.get("safe_max", limits_raw["max_pos"]),
                max_speed=limits_raw.get("max_speed", 30.0),
                forbidden_ranges=forbidden,
            )
            joint = JointDefinition(
                joint_id=jd["joint_id"],
                label=jd["label"],
                servo_channel=jd.get("servo_channel"),
                neutral_pos=jd["neutral_pos"],
                limits=limits,
                notes=jd.get("notes", ""),
                hardware_connected=jd.get("hardware_connected", False),
            )
            self._joints[joint.joint_id] = joint

        for ld in raw.get("limbs", []):
            # Validate that all referenced joints exist
            for jid in ld.get("joint_ids", []):
                if jid not in self._joints:
                    raise ValueError(
                        f"Limb '{ld['limb_id']}' references unknown joint '{jid}'"
                    )
            limb = LimbDefinition(
                limb_id=ld["limb_id"],
                label=ld["label"],
                joint_ids=ld["joint_ids"],
                notes=ld.get("notes", ""),
            )
            self._limbs[limb.limb_id] = limb

    # ── Lookup ───────────────────────────────────────────────────────

    def get_joint(self, joint_id: str) -> JointDefinition:
        if joint_id not in self._joints:
            raise KeyError(f"Unknown joint: '{joint_id}'")
        return self._joints[joint_id]

    def get_limb(self, limb_id: str) -> LimbDefinition:
        if limb_id not in self._limbs:
            raise KeyError(f"Unknown limb: '{limb_id}'")
        return self._limbs[limb_id]

    def all_joints(self) -> list[JointDefinition]:
        return list(self._joints.values())

    def all_limbs(self) -> list[LimbDefinition]:
        return list(self._limbs.values())

    def joints_for_limb(self, limb_id: str) -> list[JointDefinition]:
        limb = self.get_limb(limb_id)
        return [self._joints[jid] for jid in limb.joint_ids]

    def joint_exists(self, joint_id: str) -> bool:
        return joint_id in self._joints

    def limb_exists(self, limb_id: str) -> bool:
        return limb_id in self._limbs

    def connected_joints(self) -> list[JointDefinition]:
        """Return only joints with confirmed hardware connections."""
        return [j for j in self._joints.values() if j.hardware_connected]

    def summary(self) -> dict:
        return {
            "loaded_from": self._loaded_from,
            "joint_count": len(self._joints),
            "limb_count": len(self._limbs),
            "connected_joint_count": len(self.connected_joints()),
            "joints": [j.to_dict() for j in self._joints.values()],
            "limbs": [l.to_dict() for l in self._limbs.values()],
        }


# Module-level singleton - initialized by runtime or tests
_registry: Optional[BodyRegistry] = None


def init_registry(config_path: str) -> BodyRegistry:
    global _registry
    _registry = BodyRegistry().load(config_path)
    return _registry


def init_registry_from_dict(raw: dict) -> BodyRegistry:
    global _registry
    _registry = BodyRegistry().load_from_dict(raw)
    return _registry


def get_registry() -> BodyRegistry:
    if _registry is None:
        raise RuntimeError(
            "BodyRegistry not initialized. Call init_registry() first."
        )
    return _registry

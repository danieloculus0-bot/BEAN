"""
bean/body/limits.py

Joint limit definitions. Pure data. No hardware, no motion logic.

JointLimits defines the full safety envelope for one joint:
  - absolute min/max (hardware stops - never exceed these)
  - safe min/max (normal operating range - teaching stays here)
  - max speed (degrees or units per second)
  - forbidden ranges (specific sub-ranges that are mechanically dangerous)

ForbiddenRange defines a sub-range within min/max that is still
mechanically hazardous - e.g. a range where a cable binds,
or where the limb could strike the chassis.

The safety layer uses these to validate every motion command.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ForbiddenRange:
    """
    A position range that must never be commanded, even within min/max.
    e.g. 85-95 degrees on shoulder where cable binds.
    """
    min_pos: float
    max_pos: float
    reason: str = ""

    def contains(self, pos: float) -> bool:
        return self.min_pos <= pos <= self.max_pos

    def to_dict(self) -> dict:
        return {
            "min_pos": self.min_pos,
            "max_pos": self.max_pos,
            "reason": self.reason,
        }


@dataclass
class JointLimits:
    """
    Full safety envelope for one joint.

    Hierarchy (strictest wins):
      forbidden_ranges > safe_min/safe_max > min_pos/max_pos

    During teaching:      commands must stay within safe_min/safe_max
    During replay:        commands must stay within safe_min/safe_max
    Absolute hard stop:   min_pos/max_pos - nothing may exceed these ever
    Forbidden ranges:     rejected regardless of where they fall
    """
    min_pos: float          # absolute hardware minimum
    max_pos: float          # absolute hardware maximum
    safe_min: float         # normal operating minimum (teaching range)
    safe_max: float         # normal operating maximum (teaching range)
    max_speed: float        # maximum allowed speed (units/second)
    forbidden_ranges: list[ForbiddenRange] = field(default_factory=list)

    def __post_init__(self):
        if self.min_pos > self.max_pos:
            raise ValueError(
                f"min_pos ({self.min_pos}) must be <= max_pos ({self.max_pos})"
            )
        if self.safe_min < self.min_pos or self.safe_max > self.max_pos:
            raise ValueError(
                f"safe range [{self.safe_min}, {self.safe_max}] "
                f"must be within absolute range [{self.min_pos}, {self.max_pos}]"
            )
        if self.safe_min > self.safe_max:
            raise ValueError(
                f"safe_min ({self.safe_min}) must be <= safe_max ({self.safe_max})"
            )
        if self.max_speed <= 0:
            raise ValueError(f"max_speed must be positive, got {self.max_speed}")

    def is_within_absolute(self, pos: float) -> bool:
        return self.min_pos <= pos <= self.max_pos

    def is_within_safe(self, pos: float) -> bool:
        return self.safe_min <= pos <= self.safe_max

    def is_forbidden(self, pos: float) -> tuple[bool, str]:
        """Returns (True, reason) if pos falls in any forbidden range."""
        for fr in self.forbidden_ranges:
            if fr.contains(pos):
                return True, fr.reason or f"position {pos} in forbidden range [{fr.min_pos}, {fr.max_pos}]"
        return False, ""

    def is_speed_safe(self, speed: float) -> bool:
        return 0 < speed <= self.max_speed

    def validate(self, pos: float, speed: float) -> list[str]:
        """
        Return a list of violation strings.
        Empty list = valid command.
        """
        violations = []

        forbidden, reason = self.is_forbidden(pos)
        if forbidden:
            violations.append(f"FORBIDDEN_RANGE: {reason}")

        if not self.is_within_absolute(pos):
            violations.append(
                f"EXCEEDS_ABSOLUTE_LIMIT: {pos} not in [{self.min_pos}, {self.max_pos}]"
            )

        if not self.is_within_safe(pos):
            violations.append(
                f"OUTSIDE_SAFE_RANGE: {pos} not in [{self.safe_min}, {self.safe_max}]"
            )

        if not self.is_speed_safe(speed):
            violations.append(
                f"SPEED_VIOLATION: {speed} not in (0, {self.max_speed}]"
            )

        return violations

    def to_dict(self) -> dict:
        return {
            "min_pos": self.min_pos,
            "max_pos": self.max_pos,
            "safe_min": self.safe_min,
            "safe_max": self.safe_max,
            "max_speed": self.max_speed,
            "forbidden_ranges": [fr.to_dict() for fr in self.forbidden_ranges],
        }

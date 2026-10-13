"""Dependency-free 2D geometry for static layout feasibility checks.

Units are supplied by the caller and must be consistent (inches, mm, etc.).
This is rectangular 2D planning, not robot kinematics or verified hardware safety.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in (self.x, self.y, self.width, self.height)):
            raise ValueError("Rectangle dimensions and coordinates must be finite")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Rectangle dimensions must be positive")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def contains(self, other: Rect, *, tolerance: float = 1e-9) -> bool:
        return (self.x - tolerance <= other.x and self.y - tolerance <= other.y
                and self.right + tolerance >= other.right
                and self.bottom + tolerance >= other.bottom)

    def contains_point(self, point: tuple[float, float], *, tolerance: float = 1e-9) -> bool:
        x, y = point
        return self.x - tolerance <= x <= self.right + tolerance and self.y - tolerance <= y <= self.bottom + tolerance

    def overlaps(self, other: Rect, *, tolerance: float = 1e-9) -> bool:
        """Edge-to-edge contact alone is not a collision."""
        return (self.x < other.right - tolerance and self.right > other.x + tolerance
                and self.y < other.bottom - tolerance and self.bottom > other.y + tolerance)

    def expanded(self, margin: float) -> Rect:
        if not isfinite(margin) or margin < 0:
            raise ValueError("Clearance margin must be non-negative and finite")
        return Rect(self.x - margin, self.y - margin,
                    self.width + 2 * margin, self.height + 2 * margin)


def collision(a: Rect, b: Rect, *, a_clearance: float = 0, b_clearance: float = 0) -> bool:
    """Object exclusion zones overlap. Margins add to required separation."""
    return a.expanded(a_clearance).overlaps(b.expanded(b_clearance))

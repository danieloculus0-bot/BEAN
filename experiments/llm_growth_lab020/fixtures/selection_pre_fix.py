"""Evidence-first selection of bounded autonomous improvement opportunities.

This module ranks already-observed defects. It does not modify repositories,
grant permissions, execute proposed code, or attest that external evidence is true.
The host must supply reproducible evidence and own the sandbox and PR workflow.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ImprovementOpportunity:
    """One host-discovered, independently testable candidate."""

    identifier: str
    description: str
    evidence_refs: tuple[str, ...]
    impact: int
    reproducibility: int
    confidence: float
    risk: int
    validation_ready: bool

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("candidate identifier required")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("candidate description required")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs
        ):
            raise ValueError("at least one recorded evidence reference is required")
        for key in ("impact", "reproducibility", "risk"):
            value = getattr(self, key)
            if type(value) is not int or not 0 <= value <= 5:
                raise ValueError(f"{key} must be an integer from 0 to 5")
        if type(self.confidence) not in (int, float) or not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and between 0 and 1")
        if type(self.validation_ready) is not bool:
            raise ValueError("validation_ready must be boolean")


@dataclass(frozen=True)
class RankedOpportunity:
    opportunity: ImprovementOpportunity
    score: float


def rank_improvements(
    opportunities: list[ImprovementOpportunity], *, max_risk: int = 2
) -> list[RankedOpportunity]:
    """Rank test-ready candidates; tie-break lexically, never randomly.

    Score is a selection heuristic, not a claim that a change is beneficial.
    The independent test and observed post-change metrics decide promotion.
    """
    if type(max_risk) is not int or not 0 <= max_risk <= 5:
        raise ValueError("invalid risk budget")
    if len({candidate.identifier for candidate in opportunities}) != len(opportunities):
        raise ValueError("duplicate candidate identifier")
    candidates = [
        RankedOpportunity(
            item,
            round(4 * item.impact + 3 * item.reproducibility
                  + 3 * item.confidence - 4 * item.risk, 3),
        )
        for item in opportunities
        if item.validation_ready and item.risk <= max_risk and item.reproducibility > 0
    ]
    return sorted(candidates, key=lambda item: (-item.score, item.opportunity.identifier))

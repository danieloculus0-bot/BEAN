"""Brain 0.13 speculation and hypothesis discipline package."""

from __future__ import annotations

from .claim_types import (
    ActionPermission,
    ClaimType,
    EvidenceLevel,
    HypothesisStatus,
    VALID_ACTION_PERMISSIONS,
    VALID_CLAIM_TYPES,
    VALID_EVIDENCE_LEVELS,
    VALID_HYPOTHESIS_STATUSES,
)
from .discipline import run_full_discipline_check
from .evidence import EvidenceLink
from .hypothesis import HypothesisRecord
from .hypothesis_store import (
    add_evidence_link,
    count_all,
    count_by_status,
    get_hypothesis,
    init_speculation_schema,
    list_by_claim_type,
    list_open_hypotheses,
    persist_hypothesis,
    record_review,
    supersede_hypothesis,
    update_hypothesis_status,
)
from .maintenance import run_speculation_maintenance
from .speculative_engine import SpeculativeEngine


def init_speculation(conn=None) -> SpeculativeEngine:
    init_speculation_schema(conn)
    return SpeculativeEngine(conn)

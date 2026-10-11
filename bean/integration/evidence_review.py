"""Optional scheduled evidence review action for BEAN's durable TaskEngine.

The host supplies a read-only inbox of typed, separately attested observations.
TaskEngine may call this *named* action on its own schedule; BEAN never gains
arbitrary code, network, physical effectors, or verification authority.
Conflicting or absent evidence is reported as N/A, never silently as success.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .evidence_bridge import EvidenceBridge, SourceClaim


@dataclass(frozen=True)
class ReviewBatch:
    round_id: str
    claim_key: str
    question: str
    sources: tuple[SourceClaim, ...]

    def __post_init__(self):
        if type(self.sources) is not tuple or len(self.sources) > 32:
            raise ValueError("review sources must be a bounded tuple of 0..32")
        if not all(isinstance(item, SourceClaim) and item.round_id == self.round_id
                   for item in self.sources):
            raise ValueError("review source is invalid or belongs to another round")


class EvidenceReviewAction:
    """Host-provided named, bounded action registered with TaskEngine.

    An absent inbox item is a normal N/A (not a verified conclusion). The
    scheduler's existing WAL ledger preserves runs and blocks automatic
    replay after interrupted execution.
    """

    def __init__(
        self, bridge: EvidenceBridge,
        inbox: Callable[[], ReviewBatch | None],
    ):
        if not callable(inbox):
            raise ValueError("review inbox must be a callable host adapter")
        self.bridge = bridge
        self.inbox = inbox

    def __call__(self) -> dict:
        received = self.inbox()
        if received is None:
            return {"status": "n/a", "reason": "no_new_evidence"}
        if not isinstance(received, ReviewBatch):
            raise TypeError("review inbox must supply a typed ReviewBatch")
        self.bridge.start(received.round_id, received.claim_key, received.question)
        for candidate in received.sources:
            self.bridge.observe(candidate)
        outcome = self.bridge.finalize(received.round_id)
        return {
            "status": "verified" if outcome["status"] in
                      {"confirmed", "revised", "reaffirmed"} else "n/a",
            "reason": outcome["status"],
            "round_id": received.round_id,
            "claim_key": received.claim_key,
            "independent_origins": outcome["distinct_origins"],
            "execution_permission": "none",
        }

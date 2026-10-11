"""Safe, opt-in BEAN Core operations for a public MCP plugin.

All content is user-submitted, unauthenticated, and processed in a fresh temporary
SQLite database. No tool reaches outside sources or writes to a caller's lasting
BEAN memory. BEAN's global MemoryStore is process-scoped, so these transactions
are serialized; do not combine this adapter with another live BEAN host.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Iterator

from bean.cognition.epistemic_guard import CandidateClaim, EpistemicGuard
from bean.integration import BeanReasoningLayer, EvidenceBridge, SourceClaim
from bean.reasoning.proposal_filter import filter_proposal
from examples.restart_continuity import run_demo

_LOCK = threading.RLock()
_ALLOWED_KEYS = frozenset({"origin", "statement"})
_MAX_EVIDENCE = 12
_IDENT = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")


def _text(value: str, name: str, limit: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f"{name} must contain 1..{limit} characters")
    if "\x00" in value:
        raise ValueError(f"{name} contains invalid characters")
    return value.strip()


def _optional_text(value: str | None, name: str, limit: int) -> str | None:
    if value is None:
        return None
    return _text(value, name, limit)


def _strings(values: list[str], name: str, limit: int = 12) -> list[str]:
    if not isinstance(values, list) or len(values) > limit:
        raise ValueError(f"{name} requires a list of no more than {limit} items")
    return [_text(item, name, 250) for item in values]


@contextmanager
def _isolated_layer() -> Iterator[BeanReasoningLayer]:
    # BEAN's MemoryStore currently uses a process singleton and thread-local
    # connection; serialize to keep public calls from crossing each other's DB.
    with _LOCK:
        with tempfile.TemporaryDirectory(prefix="bean-plugin-one-call-") as tmp:
            with BeanReasoningLayer(str(Path(tmp) / "memory.sqlite3")) as layer:
                yield layer


def audit_claim(
    claim: str,
    source_ref: str | None = None,
    evidence_refs: list[str] | None = None,
    confidence: float | None = None,
    falsification_test: str | None = None,
) -> dict[str, Any]:
    """Heuristic epistemic review with BEAN's existing EpistemicGuard.

    A result of 'approved' means the built-in *heuristics* found no reason to
    downgrade; it does NOT mean an external source is authentic or a claim true.
    """
    claim = _text(claim, "claim", 1200)
    source_ref = _optional_text(source_ref, "source_ref", 250)
    falsification_test = _optional_text(falsification_test, "falsification_test", 500)
    refs = _strings(evidence_refs or [], "evidence_refs", 8)
    if confidence is not None and (type(confidence) not in (int, float) or
                                  not 0 <= confidence <= 1):
        raise ValueError("confidence must be a number between 0 and 1")
    with _isolated_layer():
        review = EpistemicGuard().audit(
            CandidateClaim(
                key="public_input.claim",
                content=claim, source_ref=source_ref,
                confidence=confidence,
                evidence=refs,
                falsification_path=falsification_test,
            ),
            persist=False,
        )
    return {
        "schema": "bean.plugin.claim_audit.v1",
        "heuristic_verdict": review.verdict.value,
        "flags": review.reasons,
        "suggested_reframe": review.repaired_content,
        "reported_source_count": len(refs) + (1 if source_ref else 0),
        "source_authentication": "not_performed",
        "truth_verification": "not_performed",
        "external_actions": "none",
        "note": ("BEAN's epistemic guard is a preliminary rule-based screen. "
                 "A clean result never proves truth. Source references here "
                 "are user-provided, not independently checked."),
    }


def compare_evidence(question: str, observations: list[dict[str, str]]) -> dict[str, Any]:
    """Analyze user-reported statements without accepting forged verification.

    Public clients cannot designate sources as trusted or independently verified.
    Contradictory positions are surfaced for the user to investigate; BEAN's
    actual EvidenceBridge is used for the bounded, unverified evidence round.
    """
    question = _text(question, "question", 500)
    if not isinstance(observations, list) or not 1 <= len(observations) <= _MAX_EVIDENCE:
        raise ValueError("observations must contain 1..12 source statements")
    items = []
    for item in observations:
        if not isinstance(item, dict) or set(item) != _ALLOWED_KEYS:
            raise ValueError("each observation must have only origin and statement")
        origin = _text(item["origin"], "origin", 80)
        statement = _text(item["statement"], "statement", 500)
        items.append((origin, statement))
    with _isolated_layer() as layer:
        bridge = EvidenceBridge(layer)
        bridge.start("round_public", "user_reported_evidence", question)
        origin_ids: dict[str, str] = {}
        for index, (origin, statement) in enumerate(items, start=1):
            identity = origin.casefold()
            if identity not in origin_ids:
                origin_ids[identity] = f"origin_{len(origin_ids)+1:02d}"
            bridge.observe(
                SourceClaim(
                    record_id=f"record_{index:02d}",
                    round_id="round_public",
                    origin=origin_ids[identity],
                    source_ref=f"submitted_record_{index:02d}",
                    value=statement,
                    verified=False, verification_ref=None,
                    observed_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        result = bridge.finalize("round_public")

    # Count reported positions but DO NOT treat reported agreement as verification.
    by_statement: dict[str, set[str]] = defaultdict(set)
    for origin, statement in items:
        by_statement[statement].add(origin.casefold())
    options = [
        {"statement": statement, "reported_independent_labels": len(origins),
         "reported_record_count": sum(s == statement for _, s in items)}
        for statement, origins in sorted(by_statement.items(), key=lambda kv: kv[0])
    ]
    return {
        "schema": "bean.plugin.evidence_comparison.v1",
        "question": question,
        "observations_received": len(items),
        "claimed_origin_labels": len(origin_ids),
        "reported_positions": options,
        "reported_positions_conflict": len(options) > 1,
        "bean_evidence_round_status": result["status"],
        "verified_independent_origins": result["distinct_origins"],
        "conclusion": None,
        "next_step": ("Reconcile contradictory statements against original records with "
                      "an authorized independent verifier." if len(options) > 1 else
                      "Corroborate this reported position against independently authenticated sources."),
        "source_authentication": "not_performed",
        "memory_lifetime": "temporary_per_tool_call",
        "external_actions": "none",
        "note": ("All statements are caller-submitted and unverified; different "
                 "labels may represent the same real-world source. This is evidence "
                 "triage, not independent research or proof of a fact."),
    }


def screen_proposal(summary: str, steps: list[str], evidence_refs: list[str] | None = None,
                    uncertainties: list[str] | None = None) -> dict[str, Any]:
    """Run BEAN's actual proposal filters; never execute proposed steps."""
    summary = _text(summary, "summary", 700)
    steps = _strings(steps, "steps", 8)
    refs = _strings(evidence_refs or [], "evidence_refs", 8)
    unknowns = _strings(uncertainties or [], "uncertainties", 8)
    checked = filter_proposal({
        "summary": summary,
        "candidate_steps": steps,
        "evidence_refs": refs,
        "uncertainties": unknowns,
    })
    return {
        "schema": "bean.plugin.proposal_screen.v1",
        "passed_basic_heuristics": all(row["passed"] for row in checked),
        "filter_results": checked,
        "requires_human_review": True,
        "execution_permission": "none",
        "note": ("Heuristic keyword filters are incomplete and may produce false positives "
                 "or negatives. Even a pass is NOT authorization or a safety certification."),
    }


def demo_restart() -> dict[str, Any]:
    """Run Core's actual two-lifecycle SQLite continuity demo with no user data."""
    with _LOCK:
        result = run_demo()
    return {
        "schema": "bean.plugin.continuity_demo.v1",
        "core_restart_proof": result,
        "note": ("Synthetic mock-provider demonstration only. Two BEAN sessions "
                 "reopen one temporary SQLite database; no cold OS restart, "
                 "external facts, persistent user memory or model learning."),
    }

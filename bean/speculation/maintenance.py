"""Maintenance helpers for speculative hypotheses."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .claim_types import EvidenceLevel, HypothesisStatus
from .hypothesis_store import count_by_status, init_speculation_schema, record_review, update_hypothesis_status


def run_speculation_maintenance(conn=None, max_open_age_hours: int = 72, dry_run: bool = False) -> dict:
    if conn is None:
        from ..memory.store import get_store
        conn = get_store()._conn()
    init_speculation_schema(conn)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(dry_run),
        "stale_open_archived": 0,
        "weak_speculation_weakened": 0,
        "contradictions_identified": 0,
        "unresolved_summary": {},
    }
    stale_rows = conn.execute(
        f"""
        SELECT hypothesis_id, evidence_level FROM speculative_hypotheses
        WHERE status='open' AND created_at < datetime('now', '-{int(max_open_age_hours)} hours')
        """
    ).fetchall()
    for row in stale_rows:
        if row["evidence_level"] in {"speculative", "hypothetical", "unknown"}:
            report["stale_open_archived"] += 1
            if not dry_run:
                update_hypothesis_status(conn, row["hypothesis_id"], HypothesisStatus.ARCHIVED.value)
                record_review(conn, row["hypothesis_id"], review_type="maintenance_archive", notes="Archived stale unresolved speculation.")
        else:
            report["weak_speculation_weakened"] += 1
            if not dry_run:
                update_hypothesis_status(conn, row["hypothesis_id"], HypothesisStatus.WEAKENED.value)
                record_review(conn, row["hypothesis_id"], review_type="maintenance_weaken", notes="Weakened stale unresolved hypothesis.")
    rows = conn.execute(
        """
        SELECT hypothesis_id, supporting_evidence_json, contradicting_evidence_json, status
        FROM speculative_hypotheses
        WHERE status NOT IN ('contradicted', 'superseded', 'archived')
        """
    ).fetchall()
    for row in rows:
        support_n = len(json.loads(row["supporting_evidence_json"] or "[]"))
        contra_n = len(json.loads(row["contradicting_evidence_json"] or "[]"))
        if contra_n >= 2 and contra_n > support_n:
            report["contradictions_identified"] += 1
            if not dry_run:
                update_hypothesis_status(conn, row["hypothesis_id"], HypothesisStatus.CONTRADICTED.value, evidence_level=EvidenceLevel.CONTRADICTED.value)
                record_review(conn, row["hypothesis_id"], review_type="maintenance_contradiction", notes=f"contradictions={contra_n}, support={support_n}")
    report["unresolved_summary"] = count_by_status(conn)
    return report

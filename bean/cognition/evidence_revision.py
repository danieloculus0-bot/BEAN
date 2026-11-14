"""OpenNARS-inspired bounded evidence revision for BEAN's existing event ledger.

Concept reference: OpenNARS for Applications, MIT, Copyright (c) 2020
The OpenNARS authors, src/Truth.c and src/Stamp.c.
Original Python adaptation, not a port of the NARS C runtime.

Frequency measures the fraction of distinct, nonconflicting source groups that
support a proposition. Confidence measures how much admissible evidence has
accumulated (w/(w+k), k=1), not the probability of being right. Duplicate
evidence stamps and repeated source claims never add independent credit.
This never promotes a world claim or authenticates host-provided provenance.
"""
from __future__ import annotations

import json
import math
import re

from ..memory.event_logger import EventType, Source, log_event
from ..memory.store import get_store

SUBTYPE = "belief_evidence_observation"
SCHEMA = "bean.nars.evidence.v1"
_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,159}\Z")
_HORIZON = 1.0


def _id(value, label, maximum=160):
    if (not isinstance(value, str) or not value
            or len(value) > maximum or not _ID.fullmatch(value)):
        raise ValueError(f"{label} must be a bounded evidence identifier")
    return value


class EvidenceReviser:
    """Evidence accounting through canonical events, not a parallel DB."""

    def __init__(self, conn=None):
        self.conn = conn or get_store()._conn()

    def observe(self, session_uuid: str, *, claim_key: str, polarity: str,
                source_ref: str, evidence_ref: str) -> dict:
        _id(session_uuid, "session_uuid")
        key = _id(claim_key, "claim_key")
        source = _id(source_ref, "source_ref")
        evidence = _id(evidence_ref, "evidence_ref")
        if polarity not in ("support", "refute"):
            raise ValueError("polarity must be support or refute")
        payload = {
            "schema": SCHEMA, "claim_key": key, "polarity": polarity,
            "source_ref": source, "evidence_ref": evidence,
            "provenance": "caller_supplied_not_independently_authenticated",
            "observation_is_world_truth": False,
        }
        # Canonical BEAN logger is the sole event writer. Duplicates remain
        # in the audit trail, but never earn additional evidential weight.
        event_id = log_event(
            session_uuid, EventType.OBSERVATION,
            f"Belief evidence submitted for {key}.", Source.SYSTEM,
            subtype=SUBTYPE, data=payload,
        )
        return {"event_id": event_id, **self.assess(key)}

    def assess(self, claim_key: str, *, max_events: int = 512) -> dict:
        key = _id(claim_key, "claim_key")
        if type(max_events) is not int or not 1 <= max_events <= 2048:
            raise ValueError("max_events must be 1..2048")
        where = ("subtype=? AND superseded_by IS NULL "
                 "AND json_extract(data,'$.claim_key')=?")
        count = self.conn.execute(
            f"SELECT COUNT(*) FROM events WHERE {where}", (SUBTYPE, key)
        ).fetchone()[0]
        if count > max_events:
            return {
                "schema": "bean.nars.truth_context.v1", "claim_key": key,
                "status": "incomplete_history", "frequency": None,
                "confidence": None, "expectation": None,
                "supporting_sources": 0, "refuting_sources": 0,
                "evidence_event_ids": [], "event_count": count,
                "history_truncated": True,
                "source_independence_authenticated": False,
                "claim_truth_verified": False,
            }
        rows = self.conn.execute(
            "SELECT id,data FROM events WHERE " + where + " ORDER BY id ASC",
            (SUBTYPE, key)
        ).fetchall()

        # One evidence stamp may not be credited across source identities or
        # with opposite polarities. Mark the stamp as contested, not first-wins.
        stamps = {}
        for row in rows:
            try:
                d = json.loads(row["data"])
            except (ValueError, TypeError):
                continue
            if d.get("schema") != SCHEMA or d.get("polarity") not in ("support", "refute"):
                continue
            if not all(isinstance(d.get(k), str) and _ID.fullmatch(d[k])
                       for k in ("evidence_ref", "source_ref")):
                continue
            stamp = d["evidence_ref"]
            stamps.setdefault(stamp, []).append((row["id"], d["source_ref"], d["polarity"]))

        sources = {}
        conflicting_stamps = set()
        duplicate_events = 0
        for stamp, observations in stamps.items():
            signatures = {(source, polarity) for _, source, polarity in observations}
            duplicate_events += len(observations) - len(signatures)
            if len(signatures) != 1:
                conflicting_stamps.add(stamp)
                continue
            event_id, source, polarity = observations[0]
            sources.setdefault(source, []).append((event_id, polarity, stamp))
        accepted = []
        conflicted_sources = []
        for source, observations in sorted(sources.items()):
            stances = {entry[1] for entry in observations}
            if len(stances) != 1:
                conflicted_sources.append(source)
                continue
            accepted.append((source, min(observations, key=lambda x: x[0])))
        supports = [x for x in accepted if x[1][1] == "support"]
        refutes = [x for x in accepted if x[1][1] == "refute"]
        n = len(accepted)
        frequency = len(supports) / n if n else None
        confidence = n / (n + _HORIZON) if n else 0.0
        expectation = (confidence * (frequency - 0.5) + 0.5) if n else 0.5
        status = ("unknown" if n == 0 else "contested"
                  if supports and refutes else "one_sided_unverified")
        return {
            "schema": "bean.nars.truth_context.v1",
            "claim_key": key, "status": status, "frequency": frequency,
            "confidence": confidence, "expectation": expectation,
            "supporting_sources": len(supports),
            "refuting_sources": len(refutes),
            "evidence_event_ids": [x[1][0] for x in accepted],
            "support_evidence_refs": [x[1][2] for x in supports][:8],
            "refute_evidence_refs": [x[1][2] for x in refutes][:8],
            "duplicate_events_discarded": duplicate_events,
            "conflicting_evidence_refs": sorted(conflicting_stamps)[:8],
            "conflicted_source_refs": conflicted_sources[:8],
            "event_count": count, "history_truncated": False,
            "source_independence_authenticated": False,
            "claim_truth_verified": False,
            "model_weights_changed": False,
        }

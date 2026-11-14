"""Focused working memory built from BEAN's existing versioned world claims.

Inspired by Letta's active-context memory design (Apache-2.0).
This implementation is original and copies no Letta code or user data.
BEAN's canonical SQLite claims and supersession history remain authoritative.
No new shadow memory, model inference or fabricated evidence is introduced.
"""
from __future__ import annotations

import json
import re
import sqlite3

# Only meaningful topic words are used to choose relevant, durable memories.
_STOP = frozenset({
    "about", "after", "again", "been", "before", "could", "does", "from",
    "have", "into", "just", "more", "need", "only", "over", "please",
    "record", "review", "should", "status", "that", "their", "them",
    "there", "these", "this", "those", "were", "what", "when",
    "where", "which", "while", "with", "would", "your",
})


def _tokens(text: str) -> tuple[str, ...]:
    words = re.findall(r"[a-z0-9]{3,}", text.casefold()[:600])
    return tuple(dict.fromkeys(w for w in words if w not in _STOP))[:10]


def recall_focused_claims(conn: sqlite3.Connection, query: str, *,
                          limit: int = 6) -> list[dict]:
    """Retrieve relevant old *active* claims, including revision provenance.

    Unlike the generic highest-confidence top-N, this scans the canonical
    cross-session SQLite index for matches without embedding dependencies.
    Every result links back to a real claim. Ranking is transparent lexical
    evidence, not semantic truth and not a learned neural improvement.
    """
    if not isinstance(query, str):
        raise TypeError("query must be text")
    if type(limit) is not int or not 1 <= limit <= 12:
        raise ValueError("limit must be 1..12")
    tokens = _tokens(query)
    if not tokens:
        return []
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='world_claims'"
    ).fetchone():
        return []

    # Rank in SQLite before the bounded result limit. A relevant old claim
    # must not be evicted by hundreds of newer unrelated observations.
    score_sql = " + ".join(
        "(CASE WHEN lower(key) LIKE ? THEN 4 ELSE 0 END) + "
        "(CASE WHEN lower(content) LIKE ? THEN 1 ELSE 0 END)"
        for _ in tokens
    )
    where_sql = " OR ".join(
        "(lower(key) LIKE ? OR lower(content) LIKE ?)" for _ in tokens
    )
    terms = [f"%{token}%" for token in tokens for _ in (0, 1)]
    rows = conn.execute(
        "SELECT id, claim_id, key, content, category, source_type, "
        "confidence, source_ref, evidence FROM world_claims "
        f"WHERE active=1 AND ({where_sql}) "
        f"ORDER BY ({score_sql}) DESC, id DESC LIMIT ?",
        (*terms, *terms, limit),
    ).fetchall()

    selected = []
    for row in rows:
        item = dict(row)
        previous = conn.execute(
            "SELECT claim_id FROM world_claims WHERE key=? AND id<? "
            "ORDER BY id DESC LIMIT 1", (item["key"], item["id"])
        ).fetchone()
        try:
            evidence = json.loads(item["evidence"] or "[]")
            if not isinstance(evidence, list):
                evidence = []
        except (TypeError, json.JSONDecodeError):
            evidence = []
        selected.append({
            "key": item["key"],
            "claim_id": item["claim_id"],
            "source_row_id": item["id"],
            "previous_claim_id": previous["claim_id"] if previous else None,
            "content": item["content"][:350],
            "category": item["category"],
            "confidence": item["confidence"],
            "source_type": item["source_type"],
            "source_ref": item["source_ref"],
            "evidence_refs": [x for x in evidence if isinstance(x, str)][:6],
            "evidence_independently_authenticated": False,
        })
    return selected

"""SQLite-backed association graph for Brain 0.9 wisdom."""

from __future__ import annotations

import uuid

from .schema import init_wisdom_schema


def add_association(from_type: str, from_id: str, to_type: str, to_id: str, association_type: str = "related", weight: float = 0.5, confidence: float = 0.5, conn=None) -> str:
    c = init_wisdom_schema(conn)
    association_id = f"assoc_{uuid.uuid4().hex[:12]}"
    c.execute(
        """
        INSERT INTO wisdom_associations
        (association_id, from_type, from_id, to_type, to_id, association_type, weight, confidence, evidence_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (association_id, from_type, from_id, to_type, to_id, association_type, float(weight), float(confidence)),
    )
    c.commit()
    return association_id


def expand(start_type: str, start_id: str, max_depth: int = 2, top_k: int = 25, min_weight: float = 0.25, conn=None) -> list[dict]:
    c = init_wisdom_schema(conn)
    seen = set()
    frontier = [(start_type, start_id, 0)]
    out: list[dict] = []
    while frontier:
        from_type, from_id, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        rows = c.execute(
            """
            SELECT * FROM wisdom_associations
            WHERE from_type=? AND from_id=? AND weight>=?
            ORDER BY weight DESC LIMIT ?
            """,
            (from_type, from_id, float(min_weight), int(top_k)),
        ).fetchall()
        for row in rows:
            item = dict(row)
            key = (item["to_type"], item["to_id"])
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
            frontier.append((item["to_type"], item["to_id"], depth + 1))
            if len(out) >= top_k:
                return out
    return out

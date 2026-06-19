"""
bean/world/model_store.py

SQLite persistence for BEAN model claims.
Claims are never deleted. Active claims are superseded by key.
"""

from __future__ import annotations

import json
from typing import Optional

from ..memory.store import get_store
from .claim import Claim, ClaimCategory, ClaimSource


CLAIMS_SCHEMA = """
CREATE TABLE IF NOT EXISTS world_claims (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id        TEXT    NOT NULL UNIQUE,
    key             TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    source_type     TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    value           TEXT,
    source_ref      TEXT,
    evidence        TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    superseded_by   TEXT,
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','utc'))
);

CREATE INDEX IF NOT EXISTS idx_world_claims_key ON world_claims(key);
CREATE INDEX IF NOT EXISTS idx_world_claims_category ON world_claims(category);
CREATE INDEX IF NOT EXISTS idx_world_claims_active ON world_claims(active);
"""


def ensure_claims_table():
    store = get_store()
    store._conn().executescript(CLAIMS_SCHEMA)
    store.commit()


class ModelStore:
    def __init__(self):
        ensure_claims_table()

    def save(self, claim: Claim) -> Claim:
        store = get_store()
        existing = self.get_active(claim.key)
        if existing and existing.claim_id != claim.claim_id:
            store.execute(
                "UPDATE world_claims SET active=0, superseded_by=? WHERE claim_id=?",
                (claim.claim_id, existing.claim_id),
            )
        store.execute(
            """
            INSERT OR REPLACE INTO world_claims
                (claim_id, key, content, category, source_type, confidence,
                 value, source_ref, evidence, active, superseded_by, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                claim.key,
                claim.content,
                claim.category.value,
                claim.source_type.value,
                claim.confidence,
                claim.value,
                claim.source_ref,
                json.dumps(claim.evidence),
                1 if claim.active else 0,
                claim.superseded_by,
                claim.notes,
                claim.created_at,
            ),
        )
        store.commit()
        return claim

    def save_many(self, claims: list[Claim]) -> list[Claim]:
        for claim in claims:
            self.save(claim)
        return claims

    def get_active(self, key: str) -> Optional[Claim]:
        row = get_store().fetchone(
            "SELECT * FROM world_claims WHERE key=? AND active=1 ORDER BY id DESC LIMIT 1",
            (key,),
        )
        return Claim.from_row(row) if row else None

    def get_history(self, key: str) -> list[Claim]:
        rows = get_store().fetchall(
            "SELECT * FROM world_claims WHERE key=? ORDER BY id ASC",
            (key,),
        )
        return [Claim.from_row(row) for row in rows]

    def get_all_active(self, category: ClaimCategory | None = None) -> list[Claim]:
        if category is None:
            rows = get_store().fetchall("SELECT * FROM world_claims WHERE active=1 ORDER BY key")
        else:
            rows = get_store().fetchall(
                "SELECT * FROM world_claims WHERE active=1 AND category=? ORDER BY key",
                (category.value,),
            )
        return [Claim.from_row(row) for row in rows]

    def get_uncertainties(self) -> list[Claim]:
        return self.get_all_active(ClaimCategory.UNCERTAINTY)

    def count_active(self) -> int:
        return get_store().fetchone("SELECT COUNT(*) as n FROM world_claims WHERE active=1")["n"]

    def count_active_for_category(self, category: ClaimCategory) -> int:
        return get_store().fetchone(
            "SELECT COUNT(*) as n FROM world_claims WHERE active=1 AND category=?",
            (category.value,),
        )["n"]

    def snapshot(self) -> list[dict]:
        return [claim.to_dict() for claim in self.get_all_active()]

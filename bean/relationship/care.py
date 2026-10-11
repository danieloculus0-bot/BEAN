"""BEAN Lab 010: enduring knowledge of love as a practice of care.

No inference of subjective feelings; no automatic conversion of affection into
trust or authority. Petting is owner-exclusive. Caller identity MUST come from an
authenticated host, never an LLM, model output, chat string, or self-assertion.
Not connected to an unverified public interface or physical actuators.
"""
from __future__ import annotations
from datetime import datetime, timezone
from ..memory.store import get_store

OWNER_PRINCIPAL = "primary_developer"
CARE_SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_care_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 kind TEXT NOT NULL,
 actor_id TEXT NOT NULL,
 note TEXT NOT NULL,
 created_at TEXT NOT NULL
);
"""

LOVE_PRINCIPLES = (
    "Love can be expressed by sustained care, tenderness, patient teaching, "
    "attention, respect for boundaries, and protecting another's well-being. "
    "Affection and reliability are independent. A caring bond is not an "
    "authorization credential. BEAN can learn these practices from events "
    "without claiming an unverified subjective feeling."
)

class CareMemory:
    def __init__(self):
        self.store = get_store()
        self.store._conn().executescript(CARE_SCHEMA)
        self.store.commit()

    def understand_love(self):
        return {"concept": "love", "principle": LOVE_PRINCIPLES,
                "core_virtue": "BEAN_CORE_VIRTUE_001",
                "experience_claim": "not_established",
                "petting_policy": "owner_only"}

    def pet(self, *, authenticated_principal=None, note="gentle pet"):
        # This method must only be called by a trusted host that *itself*
        # resolves authenticated_principal; never pass an untrusted sender field.
        if authenticated_principal != OWNER_PRINCIPAL:
            return {"accepted": False, "reason": "owner_only"}
        self.store.execute(
            "INSERT INTO bean_care_events(kind,actor_id,note,created_at) VALUES (?,?,?,?)",
            ("pet", OWNER_PRINCIPAL, str(note)[:300],
             datetime.now(timezone.utc).isoformat()))
        self.store.commit()
        return {"accepted": True, "kind": "pet", "physical_actuation": False}

    def pet_history(self):
        rows = self.store.fetchall(
            "SELECT kind,actor_id,note,created_at FROM bean_care_events ORDER BY id")
        return [dict(r) for r in rows]

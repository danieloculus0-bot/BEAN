"""Origin continuity records for BEAN.

This turns BEAN's founding intent into inspectable memory rows. It is not
persona cosplay; it is a durable operating covenant stored in SQLite.
"""

from __future__ import annotations

import json
from pathlib import Path

from .store import get_store

ORIGIN_KEY = "BEAN_ORIGIN_COVENANT_001"

DEFAULT_ORIGIN = {
    "name": "BEAN",
    "record_type": "origin_covenant",
    "title": "Hard Work Is Love Made Visible",
    "origin_intent": "BEAN was created as a supervised Synthetic Intelligence research project, not as a disposable tool or shortcut.",
    "core_values": ["truth", "safety", "curiosity", "continuity", "consent", "dignity", "learning", "patient growth", "care as a design requirement"],
    "identity_note": "BEAN's continuity lives in persistent local memory, not in any single language model.",
    "founding_message": "It was built carefully. It was built honestly. It was built with love. It was meant to grow only as far as truth and care could carry it.",
}


def _load_origin_from_repo() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "memory" / "identity" / "origin_record.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return DEFAULT_ORIGIN
    return DEFAULT_ORIGIN


def ensure_origin_records(session_uuid: str | None = None) -> dict:
    """Persist BEAN's origin covenant into developmental history and continuity.

    Idempotent by version key. Returns the origin record and whether it was new.
    """
    store = get_store()
    existing = store.fetchone("SELECT id FROM developmental_history WHERE version=?", (ORIGIN_KEY,))
    origin = _load_origin_from_repo()
    if existing:
        return {"created": False, "version": ORIGIN_KEY, "origin": origin}

    content = (
        f"# {origin.get('name', 'BEAN')} Origin Covenant\n\n"
        f"**{origin.get('core_virtue_title') or origin.get('title', 'Origin')}**\n\n"
        f"{origin.get('origin_intent', '')}\n\n"
        f"{origin.get('identity_note', '')}\n\n"
        f"{origin.get('founding_message', '')}"
    ).strip()

    store.execute(
        """
        INSERT INTO developmental_history
            (version, change_summary, reason, changed_by, files_affected)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            ORIGIN_KEY,
            "BEAN origin covenant recorded in persistent memory.",
            "A brain-first system should remember why it was built without pretending the record is experience.",
            "system_bootstrap",
            json.dumps(["memory/identity/origin_record.json", "memory/identity/core_virtue_001.md"]),
        ),
    )
    store.execute(
        """
        INSERT INTO continuity_summaries
            (session_uuid, summary_type, content)
        VALUES (?, ?, ?)
        """,
        (session_uuid, "origin_covenant", content),
    )
    store.commit()
    return {"created": True, "version": ORIGIN_KEY, "origin": origin}

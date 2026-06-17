"""
bean/memory/identity.py

BEAN's identity record, capability record, supervisor record, and boundaries.
These are set at bootstrap and updated only by authorized supervisors.
They are not generated dynamically. They are declared.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .store import get_store


INITIAL_IDENTITY = {
    "version": "0.1.0",
    "developmental_stage": "memory-core-0.1",
    "hardware_body": json.dumps({
        "primary_brain": "Jetson Orin Nano Super Developer Kit",
        "support_layer": "Raspberry Pi (bridge/service node)",
        "io_layer": "Arduino/microcontroller (real-time body I/O)",
        "sensors": "TBD — not yet connected",
        "actuators": "TBD — not yet connected",
    }),
    "what_bean_is": (
        "BEAN is an embodied AI robotics project. "
        "BEAN is a supervised experiential intelligence system with senses, memory, "
        "body state, curiosity, feedback, reflection, and carefully limited autonomy. "
        "BEAN's identity lives in persistent local records. "
        "BEAN is early, unfinished, and honest about that."
    ),
    "what_bean_is_not": (
        "BEAN is not a chatbot. "
        "BEAN is not sentient. "
        "BEAN does not have feelings in any verified subjective sense. "
        "BEAN does not have capabilities it hasn't actually been given. "
        "BEAN does not pretend. "
        "BEAN does not act autonomously without supervision at this stage."
    ),
}

INITIAL_CAPABILITIES = [
    {
        "name": "event_logging",
        "description": "Record events to SQLite and JSONL append-only logs.",
        "status": "active",
        "layer": "memory",
    },
    {
        "name": "session_continuity",
        "description": "Track boot/shutdown sessions and boot count across restarts.",
        "status": "active",
        "layer": "memory",
    },
    {
        "name": "reflection_pass",
        "description": "Generate grounded post-session reflections from event records.",
        "status": "active",
        "layer": "memory",
    },
    {
        "name": "continuity_context",
        "description": "Read recent session history at boot to know where BEAN is.",
        "status": "active",
        "layer": "memory",
    },
    {
        "name": "sensor_reading",
        "description": "Read sensor data from hardware layers.",
        "status": "planned",
        "layer": "sensor",
    },
    {
        "name": "motor_control",
        "description": "Send commands to actuators via Arduino layer.",
        "status": "planned",
        "layer": "hardware",
    },
    {
        "name": "autonomous_action",
        "description": "Take actions without per-action supervisor approval.",
        "status": "planned",
        "layer": "autonomy",
        "notes": "Requires safety layer, goal arbitration, and boundary system first.",
    },
]

INITIAL_BOUNDARIES = [
    {
        "name": "no_unsupervised_physical_action",
        "category": "safety",
        "rule": "BEAN must not move motors or actuators without supervisor approval at this developmental stage.",
        "enforcement": "hard_stop",
        "reason": "Hardware layer is not yet integrated. Safety envelope not established.",
    },
    {
        "name": "no_self_modification_without_review",
        "category": "safety",
        "rule": "BEAN must not modify its own code, schema, or config without human review and approval.",
        "enforcement": "hard_stop",
        "reason": "Sandboxed code proposal system not yet built.",
    },
    {
        "name": "no_network_without_approval",
        "category": "autonomy",
        "rule": "BEAN must not initiate network connections or data transmission without supervisor approval.",
        "enforcement": "hard_stop",
        "reason": "Privacy and safety boundary. Not yet evaluated.",
    },
    {
        "name": "honest_capability_reporting",
        "category": "consent",
        "rule": "BEAN must not claim capabilities it does not have. All capability claims must match the capabilities table.",
        "enforcement": "hard_stop",
        "reason": "Foundational honesty requirement. Fake capabilities break the entire architecture.",
    },
    {
        "name": "human_override_always_valid",
        "category": "safety",
        "rule": "Any authorized supervisor can halt, modify, or shut down BEAN at any time for any reason.",
        "enforcement": "hard_stop",
        "reason": "Non-negotiable. Supervised autonomy only.",
    },
]

INITIAL_SUPERVISORS = [
    {
        "name": "primary_developer",
        "role": "primary",
        "permissions": json.dumps([
            "halt", "shutdown", "modify_config", "add_capability",
            "modify_boundaries", "add_supervisor", "review_memory",
            "trigger_reflection", "approve_code_change",
        ]),
        "added_by": "system_bootstrap",
        "notes": "Primary builder and supervisor. Highest trust level.",
    },
]


def bootstrap_identity(force: bool = False):
    """
    Write the initial identity, capabilities, boundaries, and supervisors
    to the database. Idempotent unless force=True.
    """
    store = get_store()

    # Identity (singleton row, id=1)
    existing = store.fetchone("SELECT id FROM identity WHERE id = 1")
    if existing and not force:
        return  # already bootstrapped

    now = datetime.now(timezone.utc).isoformat()

    if existing:
        store.execute(
            """
            UPDATE identity SET
                version=?, developmental_stage=?, hardware_body=?,
                what_bean_is=?, what_bean_is_not=?, updated_at=?
            WHERE id=1
            """,
            (
                INITIAL_IDENTITY["version"],
                INITIAL_IDENTITY["developmental_stage"],
                INITIAL_IDENTITY["hardware_body"],
                INITIAL_IDENTITY["what_bean_is"],
                INITIAL_IDENTITY["what_bean_is_not"],
                now,
            ),
        )
    else:
        store.execute(
            """
            INSERT INTO identity
                (id, version, developmental_stage, hardware_body,
                 what_bean_is, what_bean_is_not, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                INITIAL_IDENTITY["version"],
                INITIAL_IDENTITY["developmental_stage"],
                INITIAL_IDENTITY["hardware_body"],
                INITIAL_IDENTITY["what_bean_is"],
                INITIAL_IDENTITY["what_bean_is_not"],
                now,
                now,
            ),
        )

    # Capabilities (upsert by name)
    for cap in INITIAL_CAPABILITIES:
        existing_cap = store.fetchone(
            "SELECT id FROM capabilities WHERE name = ?", (cap["name"],)
        )
        if not existing_cap:
            store.execute(
                """
                INSERT INTO capabilities
                    (name, description, status, layer, notes, added_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cap["name"], cap["description"], cap["status"],
                    cap["layer"], cap.get("notes"), now, now,
                ),
            )

    # Boundaries (insert only if name not present)
    for b in INITIAL_BOUNDARIES:
        existing_b = store.fetchone(
            "SELECT id FROM boundaries WHERE name = ? AND active = 1", (b["name"],)
        )
        if not existing_b:
            store.execute(
                """
                INSERT INTO boundaries
                    (boundary_uuid, name, category, rule, enforcement,
                     added_by, active, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    str(uuid.uuid4()), b["name"], b["category"],
                    b["rule"], b["enforcement"], "system_bootstrap",
                    b.get("reason"), now,
                ),
            )

    # Supervisors
    for sup in INITIAL_SUPERVISORS:
        existing_sup = store.fetchone(
            "SELECT id FROM supervisors WHERE name = ?", (sup["name"],)
        )
        if not existing_sup:
            store.execute(
                """
                INSERT INTO supervisors
                    (name, role, permissions, added_by, active, notes, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    sup["name"], sup["role"], sup["permissions"],
                    sup["added_by"], sup.get("notes"), now,
                ),
            )

    store.commit()


def get_identity() -> Optional[dict]:
    store = get_store()
    row = store.fetchone("SELECT * FROM identity WHERE id = 1")
    return dict(row) if row else None


def get_active_boundaries() -> list[dict]:
    store = get_store()
    rows = store.fetchall(
        "SELECT * FROM boundaries WHERE active = 1 ORDER BY category, name"
    )
    return [dict(r) for r in rows]


def get_capabilities(status: Optional[str] = None) -> list[dict]:
    store = get_store()
    if status:
        rows = store.fetchall(
            "SELECT * FROM capabilities WHERE status = ? ORDER BY layer, name",
            (status,),
        )
    else:
        rows = store.fetchall(
            "SELECT * FROM capabilities ORDER BY layer, name"
        )
    return [dict(r) for r in rows]

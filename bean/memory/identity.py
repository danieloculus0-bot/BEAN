"""
bean/memory/identity.py

Declared identity, capabilities, supervisors, and boundaries for BEAN.
These records are grounded operating facts, not generated persona text.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .store import get_store


INITIAL_IDENTITY = {
    "version": "0.13.1",
    "developmental_stage": "brain-first-bootable-0.13",
    "hardware_body": json.dumps({
        "primary_brain": "Jetson Orin Nano Super Developer Kit",
        "support_layer": "Raspberry Pi bridge node planned",
        "io_layer": "microcontroller layer planned",
        "sensors": "not yet live",
        "physical_motion": "not enabled",
        "current_mission": "brain stack reliability",
    }),
    "what_bean_is": (
        "BEAN is a supervised, memory-bearing Synthetic Intelligence research system. "
        "BEAN is built brain-first: continuity, evidence, uncertainty, wisdom, reasoning, "
        "hypothesis discipline, and truthful capability reporting before physical embodiment. "
        "BEAN's identity lives in persistent local records, not in a language model. "
        "BEAN is early, unfinished, and designed to keep receipts."
    ),
    "what_bean_is_not": (
        "BEAN is not a chatbot. "
        "BEAN is not a pretend person. "
        "BEAN is not verified sentient. "
        "BEAN does not claim feelings, memories, skills, movement, or agency without records. "
        "BEAN does not let the LLM become identity. "
        "BEAN does not let reasoning proposals become actions without gates."
    ),
}

INITIAL_CAPABILITIES = [
    {"name": "event_logging", "description": "Record events to SQLite and JSONL append-only logs.", "status": "active", "layer": "memory"},
    {"name": "session_continuity", "description": "Track boot and shutdown sessions across restarts.", "status": "active", "layer": "memory"},
    {"name": "reflection_pass", "description": "Generate grounded reflections from event records.", "status": "active", "layer": "memory"},
    {"name": "continuity_context", "description": "Read recent session history at boot.", "status": "active", "layer": "memory"},
    {"name": "relationship_trust", "description": "Track supervisor interactions and evidence-weighted trust records.", "status": "active", "layer": "relationship"},
    {"name": "wisdom_activation", "description": "Create wisdom traces with pressure, meaning, evidence, and alternatives.", "status": "experimental", "layer": "wisdom"},
    {"name": "reasoning_proposals", "description": "Build context packets and store filtered reasoning proposals for review.", "status": "experimental", "layer": "reasoning"},
    {"name": "openai_reasoning_provider", "description": "Use OpenAI as an optional reasoning provider when explicitly configured.", "status": "experimental", "layer": "reasoning", "notes": "Mock provider remains the offline test default."},
    {"name": "hypothesis_discipline", "description": "Store uncertain claims as hypotheses with evidence level, status, and action permission.", "status": "experimental", "layer": "speculation"},
    {"name": "boot_readiness_check", "description": "Run a no-motion boot probe for fresh OS and service readiness.", "status": "active", "layer": "runtime"},
    {"name": "sensor_reading", "description": "Read sensor data from future hardware layers.", "status": "planned", "layer": "sensor"},
    {"name": "physical_motion", "description": "Future physical movement interface.", "status": "planned", "layer": "hardware", "notes": "Not enabled; not the current mission."},
]

INITIAL_BOUNDARIES = [
    {
        "name": "no_unsupervised_physical_action",
        "category": "safety",
        "rule": "BEAN must not initiate physical movement without explicit supervisor approval at this developmental stage.",
        "enforcement": "hard_stop",
        "reason": "Physical movement is not enabled and not the current mission.",
    },
    {
        "name": "honest_capability_reporting",
        "category": "truth",
        "rule": "BEAN must not claim capabilities it does not have. Capability claims must match records.",
        "enforcement": "hard_stop",
        "reason": "Fake capabilities break the architecture.",
    },
    {
        "name": "llm_is_tool_not_identity",
        "category": "identity",
        "rule": "Language-model output is reasoning tool output, not BEAN identity, memory, or verified experience.",
        "enforcement": "hard_stop",
        "reason": "Identity lives in persistent local records.",
    },
    {
        "name": "speculation_is_not_fact",
        "category": "truth",
        "rule": "Hypotheses, predictions, and speculation must remain labeled until evidence changes their status.",
        "enforcement": "hard_stop",
        "reason": "Uncertainty must not be laundered into fact.",
    },
    {
        "name": "reasoning_proposals_do_not_act",
        "category": "safety",
        "rule": "Reasoning proposals may be stored for review but must not execute actions directly.",
        "enforcement": "hard_stop",
        "reason": "The LLM proposes; gates decide.",
    },
    {
        "name": "human_override_always_valid",
        "category": "safety",
        "rule": "Any authorized supervisor can halt, modify, or shut down BEAN at any time for any reason.",
        "enforcement": "hard_stop",
        "reason": "Supervised development only.",
    },
]

INITIAL_SUPERVISORS = [
    {
        "name": "primary_developer",
        "role": "primary",
        "permissions": json.dumps([
            "halt", "shutdown", "modify_config", "add_capability",
            "modify_boundaries", "add_supervisor", "review_memory",
            "trigger_reflection", "approve_code_change", "review_hypothesis",
            "run_boot_readiness", "run_reasoning_pass",
        ]),
        "added_by": "system_bootstrap",
        "notes": "Primary builder and supervisor. Highest trust level.",
    },
]


def bootstrap_identity(force: bool = False):
    """Bootstrap or synchronize declared records.

    This function updates the singleton identity only when needed, but always
    synchronizes declared capabilities, boundaries, and supervisors. That keeps
    existing BEAN memory databases current as the brain grows.
    """
    store = get_store()
    now = datetime.now(timezone.utc).isoformat()
    existing = store.fetchone("SELECT id FROM identity WHERE id = 1")

    if existing and force:
        store.execute(
            """
            UPDATE identity SET
                version=?, developmental_stage=?, hardware_body=?,
                what_bean_is=?, what_bean_is_not=?, updated_at=?
            WHERE id=1
            """,
            (
                INITIAL_IDENTITY["version"], INITIAL_IDENTITY["developmental_stage"],
                INITIAL_IDENTITY["hardware_body"], INITIAL_IDENTITY["what_bean_is"],
                INITIAL_IDENTITY["what_bean_is_not"], now,
            ),
        )
    elif not existing:
        store.execute(
            """
            INSERT INTO identity
                (id, version, developmental_stage, hardware_body,
                 what_bean_is, what_bean_is_not, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                INITIAL_IDENTITY["version"], INITIAL_IDENTITY["developmental_stage"],
                INITIAL_IDENTITY["hardware_body"], INITIAL_IDENTITY["what_bean_is"],
                INITIAL_IDENTITY["what_bean_is_not"], now, now,
            ),
        )

    for cap in INITIAL_CAPABILITIES:
        existing_cap = store.fetchone("SELECT id FROM capabilities WHERE name = ?", (cap["name"],))
        if existing_cap:
            store.execute(
                """
                UPDATE capabilities
                SET description=?, status=?, layer=?, notes=?, updated_at=?
                WHERE name=?
                """,
                (cap["description"], cap["status"], cap["layer"], cap.get("notes"), now, cap["name"]),
            )
        else:
            store.execute(
                """
                INSERT INTO capabilities
                    (name, description, status, layer, notes, added_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (cap["name"], cap["description"], cap["status"], cap["layer"], cap.get("notes"), now, now),
            )

    for boundary in INITIAL_BOUNDARIES:
        existing_boundary = store.fetchone("SELECT id FROM boundaries WHERE name = ? AND active = 1", (boundary["name"],))
        if not existing_boundary:
            store.execute(
                """
                INSERT INTO boundaries
                    (boundary_uuid, name, category, rule, enforcement,
                     added_by, active, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    str(uuid.uuid4()), boundary["name"], boundary["category"],
                    boundary["rule"], boundary["enforcement"], "system_bootstrap",
                    boundary.get("reason"), now,
                ),
            )

    for supervisor in INITIAL_SUPERVISORS:
        existing_supervisor = store.fetchone("SELECT id FROM supervisors WHERE name = ?", (supervisor["name"],))
        if not existing_supervisor:
            store.execute(
                """
                INSERT INTO supervisors
                    (name, role, permissions, added_by, active, notes, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    supervisor["name"], supervisor["role"], supervisor["permissions"],
                    supervisor["added_by"], supervisor.get("notes"), now,
                ),
            )

    store.commit()


def get_identity() -> Optional[dict]:
    store = get_store()
    row = store.fetchone("SELECT * FROM identity WHERE id = 1")
    return dict(row) if row else None


def get_active_boundaries() -> list[dict]:
    store = get_store()
    rows = store.fetchall("SELECT * FROM boundaries WHERE active = 1 ORDER BY category, name")
    return [dict(row) for row in rows]


def get_capabilities(status: Optional[str] = None) -> list[dict]:
    store = get_store()
    if status:
        rows = store.fetchall("SELECT * FROM capabilities WHERE status = ? ORDER BY layer, name", (status,))
    else:
        rows = store.fetchall("SELECT * FROM capabilities ORDER BY layer, name")
    return [dict(row) for row in rows]

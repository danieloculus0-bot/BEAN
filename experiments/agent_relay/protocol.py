"""Small typed agent-message contract. No unbounded human/profile text on wire."""
from __future__ import annotations

import json
import re

SCHEMA = "bean.agent_relay.v1"
MAX_BYTES = 2048
TOPICS = frozenset({"hobbies", "communication", "lifestyle", "values", "routines", "boundaries"})
DETAILS = frozenset({
    "none", "creative_making", "quiet_time", "travel", "direct_talk",
    "humor", "shared_learning", "homebody", "outdoors", "hands_on_work",
})
SIGNALS = frozenset({
    "hello", "interested", "compatible", "incompatible", "soft_mismatch",
    "ask_local", "declined", "unknown",
})
KINDS = frozenset({"hello", "probe", "reply", "review", "close"})
FIELDS = frozenset({
    "schema", "message_id", "session_id", "sender", "recipient",
    "kind", "topic", "detail", "signal",
})
IDENT = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_message(value: object) -> dict:
    """Allowlist outbound content, including model-generated proposals.

    This limits one disclosure path but does not guarantee anonymity against
    linkage, side channels or malicious agents. Private profiles remain local.
    """
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("exact typed message fields required")
    for field in ("message_id", "session_id", "sender", "recipient"):
        if not isinstance(value[field], str) or not IDENT.fullmatch(value[field]):
            raise ValueError("invalid " + field)
    if value["sender"] == value["recipient"]:
        raise ValueError("self-addressed message")
    for field, choices in (
        ("schema", {SCHEMA}), ("kind", KINDS), ("topic", TOPICS),
        ("detail", DETAILS), ("signal", SIGNALS),
    ):
        if not isinstance(value[field], str) or value[field] not in choices:
            raise ValueError("unsupported " + field)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("ascii")) > MAX_BYTES:
        raise ValueError("oversized message")
    return dict(value)


def message(*, message_id: str, session_id: str, sender: str, recipient: str,
            kind: str, topic: str, detail: str, signal: str) -> dict:
    return validate_message({
        "schema": SCHEMA, "message_id": message_id, "session_id": session_id,
        "sender": sender, "recipient": recipient,
        "kind": kind, "topic": topic, "detail": detail, "signal": signal,
    })

"""Research-only canonical SQLite event fingerprint check for analogy evaluation.

A SHA-256 digest proves byte agreement with a retrieved local row, NOT that
the event is true, independently witnessed, or semantically transferable.
No runtime policy, second journal, or inference provider is introduced.
"""
import hashlib
import json


FIELDS = ("event_uuid", "session_uuid", "event_type", "subtype",
          "summary", "data", "source", "severity", "created_at")


def canonical_event_fingerprint(store, event_uuid):
    """Return a versioned digest of an existing canonical event, else None.

    Read through the existing MemoryStore interface. Excludes mutable
    superseded_by so corrections do not rewrite original evidence identity.
    """
    if not isinstance(event_uuid, str) or not event_uuid:
        return None
    row = store.fetchone(
        "SELECT " + ", ".join(FIELDS) +
        " FROM events WHERE event_uuid = ?", (event_uuid,)
    )
    if row is None:
        return None
    payload = {name: row[name] for name in FIELDS}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return "bean-event-v1:" + hashlib.sha256(encoded).hexdigest()


def authenticate_candidate_inventory(store, inventory):
    """Fail closed if any supplied ID/digest disagrees with canonical SQLite.

    Inventory: task_id -> {event_uuid: versioned canonical event fingerprint}.
    Caller labels remain independent; authentication does not validate labels.
    """
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("nonempty candidate inventory required")
    for task, candidates in inventory.items():
        if not isinstance(candidates, dict):
            raise ValueError("candidate inventory must be a mapping")
        for event_uuid, claimed in candidates.items():
            actual = canonical_event_fingerprint(store, event_uuid)
            if actual is None or actual != claimed:
                raise ValueError("unverified canonical event for task " + str(task))
    return inventory

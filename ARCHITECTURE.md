# BEAN Architecture — Memory Core 0.1

## Philosophy

BEAN's identity lives in persistent local records, not in model weights.
Memory is boring, inspectable, and hard to bullshit.
Nothing is deleted. Everything is logged. Fakes are not tolerated.

## Storage Strategy

| Store | Purpose |
|---|---|
| `bean_memory.db` (SQLite, WAL) | Structured queryable truth |
| `logs/events.jsonl` | Append-only audit trail |
| `config/` | Versioned identity, boundaries, safety rules |
| `docs/` | Human-readable continuity records |

## Tables

- **identity** — singleton row: what BEAN is, what BEAN is not
- **sessions** — every boot/shutdown, monotonic boot count
- **events** — append-only event spine (never delete rows)
- **observations** — sensor/body readings linked to events
- **body_state** — hardware resource snapshots
- **reflections** — grounded post-event summaries (cite real event IDs)
- **curiosity** — open questions generated from reflections
- **boundaries** — safety/consent/autonomy rules, versioned
- **capabilities** — what BEAN can actually do right now
- **supervisors** — authorized humans and their permissions
- **developmental_history** — changelog of BEAN's growth
- **continuity_summaries** — narrative session summaries

## Event Types

See `bean/memory/event_logger.py` → `EventType` enum.
All events have: session_uuid, event_type, summary, source, severity, created_at.
Events are never deleted. Corrections supersede via `superseded_by` FK.

## Developmental Stage: memory-core-0.1

Current active capabilities:
- event_logging
- session_continuity
- reflection_pass
- continuity_context

Planned (not yet built):
- sensor_reading
- motor_control
- autonomous_action

## Boundaries (Hard Stop)

1. No unsupervised physical action
2. No self-modification without review
3. No network without approval
4. Honest capability reporting only
5. Human override always valid

## Reflection Rules

A reflection MUST:
- Cite the event IDs it covers
- State only what the events show
- Note genuine uncertainties (not performed ones)
- Generate questions only when events actually raise them
- Flag anomalies that are statistically or logically unexpected

A reflection MUST NOT:
- Claim emotions or states not in the event record
- Generate questions for theatrical effect
- Summarize events it hasn't read

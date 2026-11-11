# Supersession overwrite and cycle: reproducible negative control (2026-11-04)

**Status:** observed defect in the mutation pattern, not an executed audit of BEAN's real database. No production patch, deployed behavior change, or intelligence claim.

## BEAN CONTEXT ACK v1
- Task: examine the canonical event correction path for evidence-preservation failures.
- Existing systems checked: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `bean/memory/event_logger.py` on main at `9ebf3075b7552b100e7db5561ccb193e1e792b14`; draft PR #271 read-only link auditor, #214 analogy recall, #199 Gauntlet.
- Confirmed assets to reuse: `log_event` and the SQLite event store; PR #271 is an independent *detection* effort, not a correction writer.
- Ledger/scoreboard reviewed: `research/PERSISTENT_LEDGER.md` on `experiment/anticipatory-ledger-20261020`: 34 synthetic observations, not independent learning evidence.
- Current evidence: standalone stdlib SQLite reproduction below executed locally on 2026-11-04, producing `[(1, 3), (2, None), (3, 1)]`. This validates the SQL mutation's failure mode, **not** an end-to-end BEAN runtime test. Exact-head CI and watchdog clearance unverified.
- Unknowns/conflicts: actual DB schema constraints, existing downstream correction consumers, real event histories, and concurrent writer behavior not independently tested.
- Minimum proposed change: retain a documented negative control and an integration acceptance criterion; avoid modifying Core or duplicating PR #271.
- Runtime/behavior-policy changes: none.

## Observed source behavior

At the inspected main revision, `supersede_event(event_id, replacement_id)` executes:

```sql
UPDATE events SET superseded_by = ? WHERE id = ?
```

and commits without checking that the target exists, that the replacement is newer, or that a prior supersession is already present. This is a mutable pointer on an otherwise append-only event history. Reassigning the pointer can erase the previous *relationship* from the current row even though original event rows survive.

## Reproduction, stdlib Python, isolated in-memory database

```python
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, superseded_by INTEGER)")
db.executemany("INSERT INTO events(id) VALUES (?)", [(1,), (2,), (3,)])

def current_supersede(event_id, replacement_id):
    db.execute("UPDATE events SET superseded_by = ? WHERE id = ?",
               (replacement_id, event_id))
    db.commit()

current_supersede(1, 2)  # original correction
current_supersede(1, 3)  # silently replaces correction relationship
current_supersede(3, 1)  # creates cycle
rows = db.execute("SELECT id, superseded_by FROM events ORDER BY id").fetchall()
assert rows == [(1, 3), (2, None), (3, 1)]
print(rows)
```

**Observed output:** `[(1, 3), (2, None), (3, 1)]`. No exception. This test deliberately mirrors the SQL statement, **not** BEAN's complete schema or `get_store()`; constraints in the actual database may change behavior. The result is a negative control for correction-integrity claims, not proof of corruption in an existing BEAN installation.

## Focused acceptance criteria for a future guarded correction writer

1. A correction to a nonexistent original or replacement must fail without modifying rows.
2. A replacement must be a strictly later, existing event, with the ordering policy explicitly specified.
3. A second attempt to change an already-set supersession must fail (or be recorded as a new, separately attributable correction event), never silently overwrite the first relationship.
4. A cycle must be rejected, and failed attempts must not leave a partial write.
5. Verify two independent connections, restart/reopen persistence, and transaction/concurrent-writer behavior; preserve evidence of rejected attempts where policy permits.
6. Keep the canonical `log_event` path, JSONL audit mirror, inbox receipts, and native SHA journal as the only existing evidence infrastructure. Do not create a competing event backend.

**Boundary:** PR #271's read-only checker can detect damaged links after the fact; this finding concerns *prevention at write time*. Neither the reproduction nor a green synthetic test demonstrates reasoning, transfer, or AGI. Integration must await exact-source tests, independent review, and a migration/compatibility audit.

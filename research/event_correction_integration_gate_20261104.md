# Event correction integration gate: one transaction, one accountable history

Status: **review protocol only**, 2026-11-04. No deployed behavior, no claimed learning improvement.

## Evidence and source boundaries

- Main `bean/memory/event_logger.py` at reviewed main commit `9ebf3075b7552b100e7db5561ccb193e1e792b14` performs an unconditional `UPDATE events SET superseded_by = ? WHERE id = ?`, commits, and does not issue a correction receipt. It must not be called immutable simply because original event rows remain present.
- Existing SQLite `events`, JSONL `audit_mirror`, and native reasoning SHA journal are distinct evidence surfaces; do not introduce a second authoritative event store.
- Draft #273 proposes write-time guards; #274 compares conditional-update controls; #275 demonstrates missing JSONL visibility; #276 examines atomic correction and receipt; #277 examines restart replay; #278 distinguishes reconstructed mirrors from independent authentication. These are **overlapping research**, not six production-ready features.
- #212 and #213 are merged. #214 remains opt-in cross-domain lexical precedent research; #199 remains a separate Gauntlet experiment. Neither validates event-correction integrity.
- Experimental `research/PERSISTENT_LEDGER.md` reports 34 synthetic observations, not independent general intelligence. Hosted BEAN is a JavaScript adapter, not the Jetson Python Core.
- No current exact-head CI or independent watchdog clearance was established during this review. Historical passing tests do not substitute.

## One proposed integration contract (not yet implemented)

Use a **single SQLite transaction** to (1) verify source and replacement exist, (2) enforce strictly increasing integer event IDs and source `superseded_by IS NULL`, (3) set the link using a conditional update and check exactly one changed row, and (4) insert an append-only canonical correction event with old ID, replacement ID, correlation UUID, UTC timestamp, reason/evidence reference, and schema version. Roll back all steps on any failure. Preserve the preexisting event and its data unchanged. A retry with the same correlation key must return an explicitly evidenced duplicate outcome, not silently write a second receipt. Do not assume a JSONL append can participate in the SQLite transaction: reconcile the mirror **after commit**, and surface a committed-ID error if mirror I/O fails. On restart, replay from authoritative SQLite and flag any missing or contradictory receipt; never manufacture a historical receipt and call it original evidence.

This design is **conditional** on reviewing the actual production schema, store transaction semantics, existing `supersede_event` callers, and the audit mirror's replay ordering. A naive extra `store.commit()` inside `log_event` could break atomicity. Do not implement the contract by calling the current `log_event` inside an outer transaction without first refactoring its commit boundary.

## Predeclared falsification matrix

| Case | Negative control | Candidate acceptance | Evidence to retain |
| --- | --- | --- | --- |
| First valid correction | Unconditional update | Exactly one link and one correction receipt | Before/after SQLite dump and receipt UUID |
| Repeat or conflicting correction | Second unconditional update overwrites | Reject; original link and receipt unchanged | Both attempts and failure reason |
| Missing, same, or older replacement | Current SQL may accept invalid references | Reject with no writes | IDs, constraint outcome |
| Crash before transaction commit | Separate commits may strand half an operation | Neither link nor receipt persists | Fresh process exit and reopened DB |
| Crash after SQLite commit, before JSONL append | Mirror can lag | Both SQLite records persist; replay repairs mirror without inventing provenance | Reopened DB, mirror bytes, replay log |
| Tampered SQLite with deleted mirror | Snapshot rebuild copies tampering | Explicitly report that independent authentication is unavailable | Original independent digest if present; otherwise unknown |
| Concurrent writers on separate connections | Read-then-write race | At most one committed correction and one matching receipt | Barrier timing, SQLite busy/retry outcomes |
| Existing legacy corrections | Some links may predate receipts | Detect and report legacy unverifiable state, do not fabricate backfill | Audit classification and original row IDs |
| Two-hop legitimate correction | Overly strict guard may reject chains | Allow A to B, then B to C, never A to C overwrite | All three IDs and both receipts |

## Evaluation requirements

Run candidate and unchanged main baseline against the **same** synthetic generated cases and fixed seeds, with temporary on-disk SQLite files, fresh interpreter restarts, and at least two independent writer connections. Include unseen generated correction-chain lengths and adversarial orderings beyond hardcoded examples. Publish exact main/candidate SHAs, Python and SQLite versions, source test hash, all failed cases, wall-clock cost, seed list, and counts of invalid links, orphan receipts, duplicate receipts, mirror divergence, and restart mismatches. A passing synthetic suite establishes an integrity property in that environment only, **not** causal transfer, adaptation, model learning, or AGI.

## Review order and stopping rule

1. Reconcile #273-#277 into **one** reviewed implementation and one nonduplicated regression suite; retain #278 as a threat-model limitation, not an authentication claim.
2. Verify exact-head CI and independent Watchdog review, including confidentiality screening, caller compatibility and conflict status. Do not merge or deploy automatically.
3. Stop and record a negative result if candidate fails any invariant, if no authentic receipt can be distinguished from a reconstruction, or if the claimed gain is only a higher test count.

**Disposition: BLOCKED for production integration** until exact-source tests, transaction boundary audit, fresh restart/concurrency evaluation, and independent review. This document is an acceptance contract, not evidence that those tests were executed.

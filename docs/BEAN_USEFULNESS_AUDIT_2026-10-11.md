# BEAN usefulness audit — 2026-10-11

**Standard:** Can a normal operator or an outside developer perform a real recurring task, inspect the evidence, recover from a restart and see clearly when an answer is unknown? This update checks the current BEAN Core and Bridge default-branch capabilities, not the largest experimental scores.

**Scope:** publicly inspectable Python source, offline tests and recent GitHub CI on Windows/Linux. No connection to a company ERP, actual customer outcomes, live robotic hardware, proprietary records, account permissions or sustained service uptime was available or claimed. Latest cross-platform green tests establish only their explicit contracts, not intelligence or production deployment.

## What is useful now

| Use case | Operator value | Implementation and evidence | Current honest limit | Next criterion |
| --- | --- | --- | --- | --- |
| **P0 / Morning quality exception brief** | Open one locally generated HTML report and see OTD, overdue-job gaps, RMA status, and questions requiring attention | [Bridge Daily Exception Brief](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/DAILY_EXCEPTION_BRIEF.md), merged [Bridge PR #30](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/30). Four Bridge workflow families pass | Offline authorized exports only. Counts are source-reconciled, not independently authenticated; no approved customer OTD formula | Timed ten-day human-versus-BEAN shadow reporting with zero unsupported facts |
| **P0 / Durable reasoning receipt** | Show that one event and review-required proposal survive a real BEAN shutdown and reopen, not only a one-shot mock | `python -m examples.restart_continuity`, using Core SQLite and two separate sessions (new audited demo in this update) | Mock reasoning provider. Retained records do **not** prove learned skill, autonomy or independent verification | Repeated cold process restart and external host API test |
| **P1 / Export missing-data guard** | Detect absent, conflicting and incomplete report coverage as unknown, not fake zero | Core Watcher, Bridge export reliability and new Daily Exception Brief adversarial tests | Source claims are host-attested; no independent authentication or authorization | Owner-approved source readers, timestamp windows and complete-source assertions |
| **P1 / Investigation evidence revision** | Revisit a stale definition and retain contradictions and revisions | Optional Bridge EvidenceLearningLoop, [promoted PR #26](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/26) with [actual Core integration PR #27](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/27) | Requires a separate trustworthy host investigator/verifier; not a live fact-checking service or self-trained model | New uninspected documents and independent human review |
| **P1 / RMA/CAR action queue** | See owner, due date, next action, repeat defect and verified closure | RMA occurrence evidence and Core task primitives exist | **Not yet implemented as an authorized joined case-state workflow**; no assigned owner or root cause can be inferred from reason codes | Approved source schema and read-only case lifecycle pilot |
| **P1 / Maintenance or PPAP evidence finder** | Find overdue PM or current drawing/calibration/FAI revision with citation | Core memory and evidence architecture supports future indexing | No validated approved source reader, ownership/revision authority or host permissions | Narrow, domain-specific document import tests |
| **P2 / Model-backed self-repair, code races and live internet research** | Potentially reduce developer cycles | Experiment workflows and selected review-only helpers; Aider two-task baseline tied | Narrow synthetic tasks; new performance comparison was inconclusive; CI success is not general intelligence | Independent unseen tasks, genuine provider receipts, repeatable outcome deltas |
| **P2 / Robot/CAD and BEAN OS** | Research exploration and simulation | Isolated simulation branches and CI | No validated autonomous physical deployment or full OS boot is inferred | Real hardware/OS acceptance, operator safety and rollback |

The ordinal priorities are *judgments about immediate usefulness*, not numeric capability scores.

## Improvement actually shipped this pass

- **Bridge `main`:** a deterministic, one-command local **Daily Exception Brief**: `python -m ezbean.daily_brief` using a private existing export database. Generates HTML and JSON. The report suppresses unverified or conflicted numeric values, retains quarantined RMA observations as a **lower bound only**, prioritizes evidence-quality exceptions, and allows comparison with an earlier same-period snapshot. The differences are never labeled causal improvements. Synthetic and real-empty-ledger tests pass on Windows/Linux Python 3.11/3.12, plus existing Bridge workflow families. No company data is committed.
- **Core `main`, after CI acceptance of this PR:** `python -m examples.restart_continuity` demonstrates stored events, pending review proposals, distinct sessions and SQLite continuity after close/reopen. It intentionally uses the **mock** reasoning provider and a temporary database and does not call effectors or the network.
- **Documentation:** clear operator flows and test boundaries instead of claims of untested global ability.

## Evidence safeguards

1. A missing export means **N/A**, not zero. A date-quarantined RMA count is at least the observed count, not necessarily the total.
2. Shipment-line OTD is not an approved customer scorecard. No business site ranks unless both source evidence and definitions agree.
3. Snapshot deltas may reflect corrections or export times, not proof of a newly improved business process.
4. No corrective-action owner, root cause, closure, part approval, release or automated notification is guessed.
5. A model-generated statement never authenticates its own source and never authorizes external effects.
6. No real site exports, credentials, source-level identifiers or private results belong in the public BEAN repo.

## Measurable next audit: actual user value

A **ten-workday private shadow pilot** should log (a) manual preparation minutes, (b) local BEAN run minutes, (c) verification/correction minutes, (d) unsupported, conflicting or missing metrics, (e) real decisions or errors avoided, and (f) days voluntarily used. A prior audit suggested **20 minutes/week net benefit** as a target; it remains unmeasured. Success requires no fabricated facts, zero silent source gaps, explicit reviewer signoff on KPI definitions, idempotent replay, and net positive operator time saved.

**Next practical task:** a permission-aware, read-only **RMA/CAR exception queue** backed by an approved source, with accountable human-assigned owners and due dates. Keep model-rewrite and robot studies separate from this operational gate.

Related: [original daily usefulness audit](BEAN_DAY_TO_DAY_USEFULNESS_AUDIT_2026-10-10.md), [Core ↔ Bridge evidence contract](EVIDENCE_BRIDGE_READINESS.md), [Bridge report usage](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/main/docs/DAILY_EXCEPTION_BRIEF.md).

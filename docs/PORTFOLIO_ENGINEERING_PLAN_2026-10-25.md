# Portfolio engineering plan, 2026-10-25

**Scope:** public GitHub account `danieloculus0-bot`, 19 repositories at initial inspection. Main is the working integration line. Do not mistake an isolated demo, a compiled package, or passing CI for a proven production deployment.

## Ordered execution

| Stage | Repositories | Concrete work | Acceptance evidence |
| --- | --- | --- | --- |
| 0. Evidence baseline | All public repos | Enumerate current HEADs, per-HEAD check runs, open PRs, report unknown/missing status as unknown | Timestamped JSON and Markdown evidence artifacts, offline tests and scheduled/dispatch runner |
| 1. Remove genuine regressions | AIscend #106, current BEAN Core | Repair dependencies, dataset unpacking, SQLite closure and current core regression failures without replacing working mechanisms | Exact-head Windows/Linux tests, relevant run logs, merged commits and post-merge checks |
| 2. Consolidate Core | BEAN, BEAN Bridge | Keep one BEAN-owned reasoning service/journal; reconcile legacy cognition adapters; quantify O(history) retrieval/append costs and fix with measured regression tests | Tests of retention, replay, negative feedback, restart and transfer on current main |
| 3. Demonstrate causal learning | BEAN, AIscend | Verify matched controls, realistic fees, no-future-data boundaries, independent holdouts and restart/recovery; retain winners AND losers | Reproducible dataset manifest, cost/benchmark deltas, uncertainty and leakage checks |
| 4. Wire manufacturing stack | Axiom, ForgeVault, EZ-FAIR, EZstimate, ForgeQC, PM-Tracker | Define owner for each customer/drawing/version/quality record; connect released drawing to reviewed quote/FAI without silently approving measurement | Real source-to-source contract CI and review-only data identities; explicit adapter failure handling |
| 5. Deployable security | Axiom #26, ForgeVault #8, PM-Tracker #1 | Reconcile authenticated HTTP/API writes with existing desktop/browser clients; replace client-supplied actor; require secure configuration for shared access | Positive UI client acceptance and negative unauthorized/CSRF/impersonation tests; full main CI |
| 6. Portfolio maintenance | All repos, BEAN Workshop | Distinguish current code from archival lines (MFGForge/SuperForge), update owner map and current links; keep status automatically refreshed | Inventory covers all current public repos, link checks, no fabricated deployment claims |

## Order-of-operations rules

1. **Promote working implementations**, not just plans. Merge into main when the implementation is coherent and its regression effects are understood; fix subsequent defects on main. Research evidence stays immutable.
2. **One owner per durable record.** BEAN owns reasoning/learning records. Axiom owns approved manufacturing ERP records. ForgeVault owns original controlled file revisions. AIscend owns account/order/position state and trading research receipts. Adapters exchange versioned, auditable proposals and observations; copying source code is not database synchronization.
3. **A failed or unavailable check is information.** Do not claim success from previously green runs or check-free commits. Distinguish head-of-branch CI, historical receipts, local demonstration and production operation.
4. **No duplicate engines.** Before creating an inference brain, Q-store, event ledger or spreadsheet editor, inspect the existing candidate and its migration path. Prefer compatibility adapters over parallel permanent implementations.
5. **No silent public release assumptions.** Draft access-control PRs may be promoted only after verifying the existing browser and desktop usage paths. Retain rollback commit and fix any end-user regression promptly.
6. **Measure improvements on paired baselines.** Record source SHA, dataset/revision, test seed, environment, costs, accuracy/return, negative results and recovery checks. A positive simulated paper trial is not live trading profit.

## Started in this pass

- Read the current main trees and open pull requests of BEAN, AIscend, Axiom, Bridge, EZ-FAIR and ForgeVault.
- Inspected exact-head check-runs for AIscend #106, BEAN main, Axiom #26/main, ForgeVault #8 and PM-Tracker #1.
- Implemented `scripts/portfolio_health.py` to collect exact-default-branch checks and PR counts for *all current public repos* rather than maintaining a hardcoded count.
- Added `tests/test_portfolio_health.py` and `.github/workflows/portfolio-health.yml`; the workflow creates retrievable timestamped JSON/Markdown artifacts weekly and on demand.
- Security and CI remediation PRs have *not* been represented as merged or deployed based solely on a draft's green checks.

## Known live blockers at first inspection

- AIscend #106 covers regressions in NumPy imports, compressed research index fixtures and SQLite connections; exact-head CI was in progress when captured.
- Axiom #26, ForgeVault #8 and PM-Tracker #1 need client-authentication compatibility verification. Green CI alone does not establish readiness for existing desktop users.
- Axiom #27 adds same-released-drawing quote/FAI evidence, but its merge status was conflicted at first inspection.
- BEAN public knowledge and software suite metrics may be stale until generated from current HEAD evidence. Core regression jobs were still in progress at first inspection.

This is a working implementation queue, not a claim of autonomous completion or an instruction to suppress normal product testing.

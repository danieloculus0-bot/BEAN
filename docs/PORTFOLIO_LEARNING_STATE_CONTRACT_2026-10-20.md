# BEAN portfolio-wide learning contract (experimental, 2026-10-20)

**Source inventory:** 17 repositories under `danieloculus0-bot`. This is a rollout
map, not a claim that every running application already has an active learner.

## One memory, app-specific policies

Use the existing BEAN Core as the source of application-scoped learning events,
`bean.optimization.portfolio_ledger.PortfolioLedger` as a research sidecar,
and `bean.optimization.portfolio_cli` as the language-neutral JSON boundary.

* **Event history**: complete, zlib-compressed, hash-linked evidence; unique
  `(app,event_id)`; conflicting repeats rejected. Full records can be read back.
* **Active state**: SQLite Q-values are only a rebuildable derivative. Q-learning
  uses explicit signed outcomes, including losses. No reward for merely repeating
  CI or reporting that code compiled.
* **Agent context**: query by app and topic; default 2,048-byte state summary,
  retaining bounded recent receipts and useful Q-values. Exact individual events
  are fetched by ID when needed. Truncation is explicit.
* **Scope**: app IDs are separate to avoid teaching a purchasing policy with
  arcade-game rewards. An LLM can reason over receipts; weight or Q updates
  occur only from specific learning events, not automatically from prose.
* **Retention**: source events are not discarded during compaction. The local
  research SQLite file must be backed up for durable continuity. This is not a
  hosted database, GitHub append API, or background synchronizer.
* **Truth**: `kind=measured` is a caller label, not independent authentication.
  A measured outcome still needs an independently checked evaluation receipt.

## Portfolio register

| Repository | Role / legitimate trial metric | Status at this branch |
| --- | --- | --- |
| BEAN | Shared Q ledger, source memory and bounded context | **Research PR #143; CI** |
| BEAN-AI-Bridge- | Evidence ingestion, matched outcomes and replay | Existing Bridge; **portfolio CLI adapter not yet wired** |
| FUN | Emperor Gauntlet penguin decisions vs observed health/survival | **Experimental Q policy in FUN PR #1; green smoke CI** |
| venvWin | Portable offline Emperor Gauntlet package | **Experimental bundle in venvWin PR #25; packaging CI** |
| Axiom_Beta | Shared module event bus and evidence outcomes | **Optional research client in Axiom PR #22; no default subscriber** |
| AIscend | Existing BEAN research review; later realized trading results | Existing BEAN Core adapter; **portfolio TD not wired to live execution** |
| ForgeVault | Verified document revision/retrieval correctness | **Not wired** |
| EZ-FAIR | Human-checked dimension/tolerance extraction outcomes | **Not wired** |
| ForgeQC | Later verified recurrence reductions and corrective-action effectiveness | **Not wired** |
| PM-Tracker | Equipment maintenance and verified downtime effects | **Not wired** |
| MFGForge | Legacy manufacturing module/event compatibility | **Not wired** |
| SuperForge_Unofficial | Packaging and historical planning, no independent active ERP | **Not a suitable standalone learner** |
| EZ_Expedite | Verified on-time/delay outcomes | **Not wired** |
| 64- | Its own isolated tasks and measurements, separate from ERP data | **Not wired; no implicit ERP data sharing** |
| EZ-FEA | Independently checked solver error, stability, convergence | Existing evidence handoff; **Q outcomes not wired** |
| EZstimate | Signed estimate versus actual cost deltas | **Not wired** |
| JET-ERP | Deployment/build runtime and future module relay | **Not wired** |

These distinctions matter: adding a dependency or a README does not train an
application. A real app adapter must observe an outcome, submit its receipt, ask
for a relevant policy/context, apply that policy only in the tested scope, and
verify whether performance improved versus the unchanged baseline.

## Minimal integration using JSON

```bash
# With this research branch of BEAN checked out, and your own test event:
python -m bean.optimization.portfolio_cli record --db ./state/portfolio.sqlite < event.json
python -m bean.optimization.portfolio_cli context --db ./state/portfolio.sqlite --app FUN/EmperorGauntlet --query night --max-bytes 2048
python -m bean.optimization.portfolio_cli verify --db ./state/portfolio.sqlite
```

Required event fields: `app`, `event_id`, `state`, `action`,
`reward`, `next_state`, `done`, `evidence_ref`. `reward=null`
creates an observation without teaching the policy. A rewarded transition
should also declare `kind=synthetic|measured`, `revision`, and a
specific external evaluation receipt. Duplicate inputs do not count twice.

## Research acceptance before broad rollout

1. Real-source Windows/Linux CI must pass at the **exact** commit. Prior green
   checks are not evidence for an edited file.
2. Independently compare baseline with adapted candidates under matched heldout
   conditions and evaluate regressions, not just averages.
3. Prove restart state, immutable receipts, compact state reconstruction and
   exact recall of a past failure. Fix corruption or divergence before release.
4. Confirm training changes are restricted to the authorized experimental
   action surface. No silent purchasing, manufacturing approvals or trading.
5. Measure memory and run-time cost on the intended Jetson or older PC before
   making performance claims. The browser game is offline and keeps only a
   bounded *local recent* replay snapshot, separate from this full SQLite ledger.

**Not complete**: no universal continuously running BEAN service, no
cross-repo auto-installer, no general neural retriever and no proof of
unending improvement. The central contract reduces duplication while real
application adapters are built and tested progressively.

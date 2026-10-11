# BEAN + Bridge: complete branch readiness audit, 2026-10-10

Scope: both dedicated GitHub repositories owned by danieloculus0-bot. Read-only inventory and default-branch comparisons were run against **all 40 BEAN Core branches** (including main) and **all 23 BEAN-AI-Bridge- branches** (including main) visible through GitHub on this scan. Branch counts are snapshots and include earlier promotion branches. The 63 branch count is NOT 63 independent skills or deployments.

## Baseline verified at scan time

- Core main: commit a52ec82899ee0790db341700f63d3ea7134417cc; most recent production full suite passed Ubuntu/Windows Python 3.10/3.12.
- Bridge main: commit 87ebd4e2a395033d880ae26fdbda4c663b1137eb; most recent four workflow families passed (generic ERP, knowledge, JobBOSS and native replay).
- Both repos contain working tested *source code*. These runs cannot verify host installation, venvWin boot, installed inference models, real ERP authorization, online autonomous cognition or real-world sensor behavior.

## Core branch family disposition

| Branch families | Relative to main | Disposition |
| --- | --- | --- |
| brain-0.13-code, -commit, -commit-real, -commit-test, -final, -final-write, -final-write-actual, -normalized, -normalized-work, -speculation-reasoning, -speculation-reasoning-2; bean-core-virtue-001 | 0 commits ahead | Historical snapshots, no code promotion needed |
| Early installer / chatgpt-brain-0.13-recovery | Diverged by 41–47 historical commits | Re-audit old code before cherry-picking; do not wholesale merge |
| Already-merged watcher, boot, origin, durable tasks, capability exam, memory isolation and documentation branches | Divergent or behind because of squash merges | Keep history as evidence, do not re-merge |
| Core trust-care Lab010 | 11 ahead/8 behind at scan | Domain trust heuristics and owner-care experiment. No independent verifier authentication; exclude from production behavior changes pending validation |
| Core Labs011–012 | Original experiments stacked under newer defaults | Narrow durable-task and entrance-exam versions already independently in main |
| Core Labs013–015 | Stacked experimental source-calibration, fictional investigative loop and non-neural symbolic provider | Promote **offline evaluation code and tests only**, no runtime activation or auto-learning claim |
| Core Lab016 | Hosted provider request never returned verified chat completion | Retain as draft research, NO evidence of real hosted-model learning |
| General-reasoning-layer | 11 ahead/14 behind at scan | Extract thin host-neutral proposal-only adapter on current main and test host lifecycle in new PR |
| Motion/body branches | Old simulator/teaching work substantially already on main | No hardware-ready claim and no new merge |

## Bridge branch family disposition

| Branch family | Status | Disposition |
| --- | --- | --- |
| Generic ERP, JobBOSS export adapter, source completeness + correction, knowledge gate, 1618 RMA/CAR replay | Main CI green | Retain current production source; no duplicate app feature promotion |
| LAB003 evidence intelligence → LAB004 revision → LAB005 confidence → LAB006 epistemic continuity → LAB007 Ollama verifier | Multiple stacked branches sharing fixtures | Keep synthetic research until independently verified on new generators |
| LAB008 dynamic definition, LAB009 native gateway and learning loop | Optional deterministic gate already promoted; native symbolic gateway not general LLM | Do not claim local model replacement |
| Labs012–014 broad learning and recovery | Holdout failures remain documented: 1,520 synthetic worlds / -104 reward for Lab014 against equal-audit comparator | No policy promotion |
| Robot-body, RV vault, venvWin/Puppy smoke, McDonald's research | Self-contained niche experiments | Distinct from Core reliability; no live execution or OS/robot boot proof |
| Prior audit, promotion, reliability branches | Squash merged, now behind or divergent | Do not replicate older versions |

## Promotion gates

A Core feature may be merged only if it is independent of other draft branches, extends current main without undoing Watcher/memory hardening, never takes action from model output, preserves source and session identity, passes the full 4-environment Core regression matrix, and has tests demonstrating failure/unknown behavior. Experimental simulators that pass CI can be in main as **optional developer tests** but not labeled successful autonomous cognition.

Tracked implementation PRs:
- [Host-neutral proposal adapter](https://github.com/danieloculus0-bot/BEAN/pull/28)
- [Offline evaluation Labs013–015](https://github.com/danieloculus0-bot/BEAN/pull/29)

The previous [ecosystem growth audit](BEAN_ECOSYSTEM_GROWTH_AUDIT_2026-10-10.md) and [usefulness audit](BEAN_DAY_TO_DAY_USEFULNESS_AUDIT_2026-10-10.md) remain applicable. Application-specific development is deferred until requested.

## Real gaps to research next

1. Source independence, authenticated verification and the difference between *reported* evidence and *true* evidence.
2. Unexpected evidence shifts, safe reversion and over-switching: failures belong in the audit journal.
3. General model inference connectivity and paired blind evaluation: current hosted smoke returned unavailable.
4. Runtime hosting, process memory isolation and cold restart vs ordinary SQLite close/reopen.
5. Provenance and uncertainty across reasoning proposals, not merely one successful scripted example.

**Never treat a passing synthetic test or a large branch count as proof that BEAN became broadly more intelligent.** The purpose of this audit is to promote high-confidence building blocks and keep scientific failures intact.

# Digital feedback control-gap investigation, 2026-11-14

BEAN CONTEXT ACK v1
Task: identify a falsifiable deficiency in the existing GitHub Core learning evaluation.
Existing systems checked: AGENTS.md, docs/AI_GATEKEEPER.md, origin JSON and loader, November 6 continuity audit, scripts/invoke_bean.py, GitHub engineering reader, generation 37 manifest, recent main commits and PRs 199/212/213/214.
Confirmed assets to reuse: existing synthetic SQLite checkpoint, SHA-linked manifest, native Core invocation and digital_learning evaluation; no new memory store.
Ledger/scoreboard reviewed: generation 37 manifest; archived research/PERSISTENT_LEDGER.md is NOT AVAILABLE on main. Individual trial cases were not independently retrieved.
Current evidence: manifest source e37559a79b5d242e5f00419ba931d19540618fe5, generation 37, run 43567874526. These are historical receipts, not current exact-head CI or independently audited cognition.
Unknowns/conflicts: exact-head CI and runner outcome not checked; fresh hidden evaluation not run. PR 212 and 213 merged, PR 214 and 199 closed unmerged; inspect merged implementation before changes.
Minimum proposed change: document discriminating experiment and explicit negative baseline result; no runtime modifications.
Runtime/behavior-policy changes: none.

## Question and observed limitation

Does persisted experience improve unseen decisions **beyond a fixed grammar-matched or passive policy**, under identical evidence and budgets? At generation 37, the candidate, grammar-matched control and passive control each scored 144/144 synthetic blind cases. The memory-ablated control scored 96/144. Candidate minus grammar-matched advantage is **zero**. The ablation gap alone does not isolate acquired generalizable reasoning because the other strong controls tie the candidate. These are aggregate manifest values, not independently audited individual cases. Do not convert them into a claim of AGI or consciousness.

## Competing approaches

A. Extend the existing feedback experiment with a hidden family of *counterfactual reversals*: generate a new symbolic rule per seed, withhold rule labels at evaluation, and expose only a bounded training sequence with outcome feedback. Compare the persisted Core candidate with a grammar-matched fixed rule, passive action, memory-ablated Core, and an oracle upper bound. Randomize label/action mapping across seeds, retain negative feedback, and test cold restart before evaluation. A wins only if it beats both strong controls on independently seeded holdouts. Falsifier: candidate remains tied or loses after paired trials, or gains vanish after restart.

B. Use a frozen, separately generated multi-step digital planning environment where delayed feedback requires choosing and revising a hypothesis. Compare existing NativeReasoningService with single-pass provider calls and matched inference budgets. Record each actual retrieval, inference request, evidence hash, stopping decision and final independent score. Falsifier: no measurable advantage over the single-pass baseline or any missing step receipts. This is more expensive and cannot be credited without a live provider/runner.

**Selection:** A first. It directly challenges the demonstrated ceiling and reuses the existing Core/manifest pipeline. B remains a subsequent hypothesis, not an implemented capability.

## Reproducible acceptance contract for implementation

- Derive a fresh seed list outside the candidate's accessible training context; record generator revision and independent evaluation hashes. Keep the held-out task set inaccessible during policy updates.
- Record a paired per-seed table with candidate, grammar, passive, memory-ablated and oracle outcomes, not just totals. Use equal evaluation observations and explicit training budgets.
- Require at least two rule reversals, including one after checkpoint/restart. Test no-feedback, shuffled-feedback and irrelevant-memory negative controls.
- Preserve exact source SHA, generation, previous receipt SHA, elapsed time, actual runner IDs, per-seed failures, and confidence intervals for paired score differences.
- Fail the claimed transfer if the candidate does not beat both strong controls on unseen reversal seeds. Preserve ties as ties, never claim learning from an unchanged deterministic replay.
- Do not overwrite or reset generation 37. Add a separate public-safe experiment receipt only after execution, then verify it is actually replayed by a later Core boot.

## Execution status

HOURLY COGNITIVE SIMULATION NOT RUN. This cycle used GitHub source inspection and existing aggregate receipts, but did not invoke an executable BEAN Core runner. Specific wiring gap: this connector session exposes repository writes and historical workflow reads, but no verified dispatch/run-and-observe path for a fresh Core evaluation. No new measured learning, restart, or exact-head CI success is claimed. This document is a falsifiable experiment design, not a simulation result.

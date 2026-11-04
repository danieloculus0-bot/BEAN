# Causal transfer: identifiability and intervention audit (2026-11-04)

**Status:** research-only, pre-execution failure audit. No BEAN Core runtime, memory schema, hardware, or inference-provider changes. This note complements the falsifiable transfer protocol in draft PR #269; it is not another benchmark or event store.

## BEAN CONTEXT ACK v1

- Task: specify a falsifiable causal-identifiability audit before interpreting cross-domain analogy wins as transferable reasoning.
- Existing systems checked: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `bean/memory/event_logger.py` on main `9ebf3075b7552b100e7db5561ccb193e1e792b14`; PRs #199, #212, #213, #214, #269.
- Confirmed assets to reuse: canonical SQLite events and JSONL mirror; merged event receipts (#212) and uncertain interpretation (#213); opt-in precedent recall (#214, draft); Gauntlet (#199, draft); preregistered transfer protocol (#269, draft).
- Ledger/scoreboard reviewed: `research/PERSISTENT_LEDGER.md` on `experiment/anticipatory-ledger-20261020`; its 34 observations are explicitly synthetic, not independent acquisition.
- Current evidence: main exact-head PR-triggered Actions lookup returned no runs; no independent held-out causal transfer run was inspected. No watchdog clearance established.
- Unknowns/conflicts: causal independence of task families, intervention validity, latent confounders, branch integration, watchdog findings.
- Minimum proposed change: a bounded experimental audit and failure matrix, without modifying existing scoring or receipt implementations.
- Runtime/behavior-policy changes: none.

## Identifiability failure that the current synthetic proxy inversion does not settle

A predictor can survive a proxy reversal without representing the true causal mechanism. For example, let latent context `U` cause both observed feature `X` and target `Y`; an intervention on a different proxy `P` can reverse `P` while leaving the spurious `X <- U -> Y` association intact. A successful `P`-reversal benchmark therefore does **not** establish that `X` causes `Y`. Similarly, selecting features after inspecting intervention outcomes leaks test information into the proposed mechanism.

The falsifiable distinction is **predictive invariance under a declared intervention family**, not unrestricted causal discovery. Even invariance is insufficient if all tested environments share an unmeasured confounder. Document the intervention target, assignment process, compliance, measured variables, and any plausible backdoor path before evaluation.

## Paired experiment design (proposal, not executed)

1. Generate three synthetic task families with disjoint structural equations and vocabularies: binary fault diagnosis, inventory-flow routing, and abstract switchboard planning. Use neutral synthetic data only. Separate generator seeds and latent-parameter draws by family; do not merely rename the same causal graph.
2. Freeze the candidate selection algorithm, feature list, baseline implementations, sample budget, family assignment, seed derivation, and decision threshold before opening any test split. Persist the plan hash and source SHA in a receipt.
3. For each family, allocate a training environment, an intervention-selection environment, and a **fresh, sealed** evaluation environment. Evaluate only once per frozen candidate, or apply the predeclared sequential-testing correction from draft #268.
4. Compare under identical observation, compute, and action budgets: causal-structure candidate, strongest observational predictor, lexical-nearest precedent, shuffled-outcome precedent, and no-memory baseline. Include a no-intervention control to expose whether intervention information actually helps.
5. In the sealed evaluation, independently randomize `do(P)` and `do(X)` where the structural model permits it. Include a second unseen confounder distribution and a deliberately broken intervention (noncompliance) as a **negative control**, not as valid causal evidence.
6. Require a restart between training and sealed evaluation. Reload only persisted approved state and record what was actually available to the agent. A model-authored explanation does not count as a successful prediction or action.

## Failure matrix and interpretation

| Probe | Required diagnostic | Interpretation if failed |
| --- | --- | --- |
| Proxy reversal | Compare against observational predictor on unseen proxy sign | Proxy reliance not ruled out |
| Intervention on selected feature | Measure outcome change under assigned `do(X)` | No evidence that selected feature is causal |
| Confounder shift | Resample latent `U` on held-out graph | Apparent invariant predictor may be confounded |
| Invalid intervention | Record compliance and reject contaminated rows | Intervention effect not identifiable |
| Vocabulary swap | Change tokens while preserving mechanism | Lexical memorization possible |
| Mechanism swap | Preserve tokens while changing equations | Surface analogy may be mistaken for transfer |
| Shuffled outcomes | Re-run with outcome mapping permuted | Leakage or uncontrolled shortcut if gains persist |
| Restart | Compare before/after persisted-state reload | No demonstrated durable adaptation |
| Family aggregation | Count independent structural families, not rows | Inflated statistical evidence |

All failures, abstentions, ties, and invalid intervention receipts must remain visible. No feature can be declared causal solely because it wins a synthetic accuracy comparison.

## Receipt fields and audit requirements

Use existing canonical event logging for observed actions and outcomes. Store research manifests adjacent to experiments, not as a second event backend. Each experimental receipt should identify: `plan_sha256`, `source_commit`, `generator_revision`, `family_id`, `environment_id`, `seed`, `intervention_target`, `assignment_method`, `compliance`, `candidate_id`, `baseline_id`, `budget`, `split_role`, `outcome`, `validity_reason`, and `prior_receipt_id` for revisions. Hashes identify artifacts; they do not independently prove randomization, independence, or correctness. Corrections append new receipts with links to old ones, never erase unfavorable observations.

**Decision rule:** report per-family paired differences and negative controls first. Abstain from transfer claims if any sealed split was used for model/feature selection, if intervention validity cannot be established, or if claimed independent families share a generator mechanism. Do not aggregate invalid cases into a positive score. Independent reviewers should be able to reproduce the generator, split, interventions, and decision from exact revisions.

## Evidence and next gate

This is a methodological analysis, not an executed test or measured improvement. A future implementation must run the existing candidate and controls against sealed independent generators and archive exact observed results, including hard failures. The draft research stack requires integration and watchdog review. **BLOCKED for capability claims** until independently acquired, held-out, restart-persistent gains beat strong baselines across genuinely distinct families. No claim of AGI or deployed Jetson behavior.

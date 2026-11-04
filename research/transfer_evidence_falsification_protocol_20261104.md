# BEAN transfer evidence: preregistered falsification protocol (2026-11-04)

**Status:** research design, not an executed benchmark or a claim of general intelligence. Scope is the existing BEAN Core event/receipt and analogy workstream. This note adds no event store, model, policy, inference provider, or runtime behavior.

## Evidence inventory and limitations

- Main was inspected at merge commit `9ebf3075b7552b100e7db5561ccb193e1e792b14`. Canonical history is `bean/memory/event_logger.py`: SQLite event rows, with JSONL mirror reconciliation. Do not substitute a separate evaluation database for this canonical record.
- The ledger specification on `experiment/anticipatory-ledger-20261020` describes 34 synthetic observations and a reversible compressed snapshot. This is **not** proof of independently learned transfer; its own text marks the scoring state as proposed.
- The hosted BEAN connector reports a JavaScript memory adapter, not the local Python Core or Jetson. Its recalled ledger descriptions are caller-supplied and not independently verified.
- PRs #199, #214 and #261 through #268 must be checked for overlap and exact-head CI before integrating any implementation. A regression-test count alone is not a capability result.
- GitHub Actions returned **zero PR-triggered workflow runs** for the inspected main merge SHA; this is an API-scope observation, not a claim that all CI is absent. Independent watchdog clearance is not established.

## Falsifiable question

Can a fixed-budget BEAN precedent-recall policy use **outcome-validated causal structure** from a previously unseen source domain to improve decisions in a different, freshly generated target domain, after a process restart, beyond both a lexical retrieval control and a no-memory control?

A similarity match is a *candidate hypothesis*. Transfer counts only when a target outcome validates a proposed intervention. Failure and abstention must be retained.

## Preregistration before any target evaluation

1. Freeze code SHA, retrieval corpus SHA, model/provider revision (or `none`), seed list, compute/time budget, hypothesis-selection rule, and scoring script SHA. Generate independent target families with a separate seed stream after freezing. Do not tune on those families.
2. Use at least four structurally distinct synthetic domains, with counterbalanced labels and surface vocabulary. Split by **generating causal mechanism/family**, not by text or case ID. Include synonym-only distractors, reversed causal direction, proxy correlation inversion, and a null environment with no transferable mechanism.
3. Randomize matched cases across four arms: **A** no precedent memory; **B** lexical nearest-neighbor; **C** outcome-validated structural precedent; **D** shuffled source-outcome control. Keep candidate count, tool calls, tokens and decision time matched. A structural policy that consumes more resources must be reported separately, not credited with an unqualified gain.
4. Allow a bounded source learning phase with actual outcome feedback, then freeze the source receipts. Evaluate target actions **without** target labels until after predictions are recorded. For online adaptation, provide the same target feedback schedule to all arms and report before-feedback and after-feedback results separately.
5. Restart the process between source acquisition and target evaluation. Reconstruct the same bounded memory from canonical persisted receipts. Verify event IDs, evidence hashes, supersession annotations, and negative outcomes before and after restart. A restart that loses any record is a failure, not an excluded trial.
6. Primary metric: target intervention success per independent mechanism family, paired C versus the **strongest** of A, B, D selected *on a separate development split*. Secondary metrics: calibration/Brier score, abstention coverage, false-transfer rate on null families, tokens/latency, and persistence fidelity. Report all arms and all families.
7. Statistical unit is the independent causal family. Report family-level paired differences, uncertainty intervals, and a preregistered exact paired sign test. Correct for multiple planned primary contrasts; do not repeatedly peek at held-out results and then report an unadjusted p-value. A family with conflicting trials is a mixed/negative outcome, not multiple independent votes.
8. Success threshold: positive held-out family-level gain over the strongest control with adjusted statistical support, non-inferior null-family false-transfer rate, intact restart persistence, and no budget violation. **Any** missing condition means inconclusive or failed, not AGI. Even success is narrow evidence of transfer, not broad general intelligence.

## Required receipt fields

Each run should append a versioned research receipt through the canonical event interface (or store a separate *research artifact* linked by event UUID when the evaluator runs outside Core): experiment ID, frozen code SHA, corpus SHA, generator revision, family ID, source/target domain IDs, random seed, policy arm, budget, predicted intervention, observed outcome, comparator, uncertainty, timestamp, restart identifier, evidence digest, and explicit `synthetic` status. Abstractions are revisable interpretations; factual observations and negative outcomes remain append-only. Never write invented outcomes to Core.

## Failure probes that must remain visible

- **Lexical trap:** near-identical words with opposite causal effects; C should reject a false analogy.
- **Mechanism-preserving rename:** disjoint vocabulary with same causal graph; C should transfer without keyword overlap.
- **Proxy reversal:** training correlation changes sign under target intervention; a proxy-based policy should fail visibly.
- **No-analogy null:** none of the sources apply; abstention should beat confident false transfer.
- **Persistence fault:** restart from receipts with one mirror write interrupted; SQLite authority and reconciliation must be checked without duplicating an event.
- **Confounded families:** many surface variants of one mechanism must count as one independent unit.
- **Negative source evidence:** previously failed intervention must reduce, not boost, subsequent confidence.

## Decision and next implementation gate

First audit existing draft PR implementations for equivalent generators, evaluators and provenance fields. Reuse those rather than implementing another selector or journal. If any prerequisite is missing, add the smallest isolated adapter or test to the existing research branch. Do not merge or deploy without independent tests and watchdog review. No Jetson, hardware, employer data or Axiom changes are authorized by this protocol.

**Current verdict:** protocol specified; independent held-out run **NOT EXECUTED**; transfer gain **UNKNOWN**; AGI conclusion **NOT SUPPORTED**.

# Paired transfer evidence: dependency-family control (2026-11-03)

BEAN CONTEXT ACK v1
Task: Add an isolated, descriptive paired transfer evidence accounting control.
Existing systems checked: AGENTS.md; docs/AI_GATEKEEPER.md; main event_logger.py and reasoning_service.py; PR #249; open analogy research PRs #241-#248.
Confirmed assets to reuse: existing Core ExperienceBank, SQLite event history and SHA journal; no new store, learner or policy.
Ledger/scoreboard reviewed: experimental research/PERSISTENT_LEDGER.md, a specification and synthetic snapshot; no independently verified held-out transfer records.
Current evidence: main and PR #249 inspected, but exact-head CI and watchdog status not independently established for this new branch.
Unknowns/conflicts: no independently labeled cross-domain transfer evaluation; family assignments require independent review.
Minimum proposed change: pure descriptive evaluator and three synthetic unit controls, not wired into runtime.
Runtime/behavior-policy changes: none.

## Deficiency and control
Twenty rephrasings of one causal problem are twenty paired observations but only **one dependency family**. Treating them as twenty independent transfers exaggerates evidence. This evaluator retains case-level wins, losses, ties and a conservative family-level breakdown, including negative results. It makes no significance claim and does not authenticate source labels.

## Prospective protocol
Before evaluation, freeze independent case labels, dependency-family assignments, model/policy revisions, seed, budget, and a separate held-out/OOD split. Evaluate unchanged baseline and candidate on exactly matched cases; store receipts and source hashes in the existing canonical event system, not this evaluator. Assign a shared family to paraphrases, shared primitive templates and derived variants. Report both raw case outcomes and family totals. Do not infer statistical independence of families merely because their IDs differ.

## Evidence limits
Unit tests are arithmetic and validation fixtures, not actual BEAN transfer or AGI performance. No Jetson, private data, deployment or main merge. Exact-head CI must be inspected before promotion.

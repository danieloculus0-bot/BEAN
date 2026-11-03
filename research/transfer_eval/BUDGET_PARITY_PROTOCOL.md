# Paired resource-budget parity audit (2026-11-03)

BEAN CONTEXT ACK v1
Task: prevent hidden resource advantage in paired cross-domain transfer evaluations.
Existing systems checked: AGENTS.md; docs/AI_GATEKEEPER.md; PRs #199, #212-#214, #250-#254; paired_families.py and split_leakage.py on #254.
Confirmed assets to reuse: existing research/transfer_eval family and provenance controls; canonical Core event logger unchanged.
Ledger/scoreboard reviewed: gatekeeper inventory; independent original-case scoreboards NOT CHECKED; no authenticated held-out results available.
Current evidence: parent #254 exact-head workflow query returned zero runs. Five synthetic local budget-control tests passed before GitHub submission; exact submitted GitHub test revision requires CI.
Unknowns/conflicts: independent watchdog findings not verified; source-side budget measurements not authenticated.
Minimum proposed change: pure stdlib metadata audit and five negative controls on an isolated branch.
Runtime/behavior-policy changes: none.

## Reproducible protocol

Record case_id and baseline/candidate budgets **before scoring**. For each side report nonnegative integer inference_tokens, tool_calls, and training_updates. Evaluate each paired case with the same resource accounting convention. The audit flags *any* candidate per-case excess, even when aggregate totals match, and rejects missing/duplicate cases, malformed budgets, negative values and boolean masquerading as integer counts. No automatic resource normalization, no silent exclusion of failed trials. Preserve negative results and original receipts in the existing event/ledger systems. Equal declared budgets are not proof of equal wall-clock, model capacity, search quality, data access, or actual execution.

Run: `python -m unittest research.transfer_eval.test_budget_parity -v`.
Local precursor: 5 synthetic tests passed; independent GitHub CI and watchdog pending. No BEAN acquisition or AGI claim.

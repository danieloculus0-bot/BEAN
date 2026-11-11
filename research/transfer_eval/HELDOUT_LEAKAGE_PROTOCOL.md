# Held-out provenance leakage audit, 2026-11-03

BEAN CONTEXT ACK v1
Task: detect train/evaluation evidence reuse before asserting transfer.
Existing systems checked: AGENTS.md, docs/AI_GATEKEEPER.md, PRs #199, #212-#214, #249-#252.
Confirmed assets to reuse: research/transfer_eval paired evaluator, family sensitivity and domain coverage; existing canonical event logger remains unchanged.
Ledger/scoreboard reviewed: gatekeeper inventory and #252 protocol; independent held-out receipts unavailable.
Current evidence: parent #252 exact-head workflow query returned no runs. Five local synthetic negative controls passed.
Unknowns/conflicts: no independently authenticated source-family labels or watchdog clearance.
Minimum proposed change: isolated fail-closed metadata leakage audit, no runtime wiring.
Runtime/behavior-policy changes: none.

## Protocol
Preregister training and held-out splits, case IDs, dependency-family IDs, original source hashes, receipt hashes, seeds, budgets and evaluator revision before looking at outcomes. Reject an independent held-out claim if any identifier overlaps across splits. Duplicate case or receipt IDs inside a split and missing identifiers raise errors. The audit deliberately does not establish semantic independence, authenticate hashes or validate actual BEAN acquisition. Independent reviewers must examine shared causal templates, contamination and data provenance. Keep failures and original receipts in existing append-only evidence systems.

## Verification and limits
Local stdlib unittest execution: five synthetic controls passed, including family/source/receipt leakage and invalid metadata. GitHub exact-head CI and independent watchdog review remain pending. No deployment, merge, hardware, employer data or AGI claim.

# Default GoalCycle digital experiment gap, November 16, 2026

BEAN CONTEXT ACK v1

Task: investigate an integrated digital experiment path without a second brain or duplicate goal-repetition fix.
Existing systems checked: AGENTS.md, docs/AI_GATEKEEPER.md, docs/SOFTWARE_AUDIT_SKILL.md, docs/OPEN_AGENT_PATTERNS_2026_11_14.md, canonical origin record and loader, bean/cognition/goal_state.py, bean_run.py, research/github_brain/manifest.json and GOAL_REPETITION_2026-11-15.md. Hosted BEAN status, recall(include_older=true), audit_claim, compare_evidence and screen_proposal were called. Hosted adapter revision 163f3e2 is NOT Python Core.
Confirmed assets: GoalStateEngine persisted experiment signatures; bean.runtime.goal_cycle.GoalCycle; existing SQLite/event history and public-safe checkpoint.
Ledger: manifest generation 56, 56 boots, 1876 events, source ea9db993e4ac034e02831ea1f0ac44b25878622c, GitHub run 43948485531; synthetic-only. Candidate 144/144, passive 144/144, grammar-matched 144/144: no strong-control gain.
Current evidence: GitHub recent commit search returned c96fe0ccc8f31c899c62216dbd26553124726f20. Exact-head CI and runtime execution at this SHA NOT VERIFIED.
Unknowns: latest Watchdog, full repository inventory, executable experiment candidates and independently audited held-out cases NOT CHECKED.
Minimum change: source-grounded negative result and falsifiable integration contract. Runtime changes: none.

## Deficiency

Current `bean/cognition/goal_state.py` emits `run_experiment` proposals for structured `bean.cognition.experiment.v1` questions and preserves unchanged experiment identity across restarts/outcomes. Current `bean_run.py` constructs default GoalCycle with only `update_models` and `run_reflection` registered. Thus the default GoalCycle cannot execute its native structured experiment proposals. This does NOT establish absence of separate opt-in experimental runners.

## Competing approaches

A. Reuse an existing bounded experiment executor via the existing GoalCycle registry. Falsifier: no executor has validated typed inputs, fixed budgets, independent evaluation and restart-safe receipts, or interrupted actions are replayed.

B. Bridge the existing opt-in TaskEngine action registry to GoalCycle. Falsifier: its outcome cannot be associated with the originating native goal across restarts without introducing another persistence owner.

Before implementation, inspect `bean/runtime/goal_cycle.py`, `bean/runtime/task_engine.py`, native research/experiment implementations, open PRs and actual tests. Prefer existing modules, never create a second SQLite brain.

## Acceptance contract

Use disposable synthetic SQLite, fixed seed, explicit observation and competing hypotheses, bounded retrieval/action/evaluation with source hashes, negative control, recorded failure, restart, then independent held-out task. Compare equal-budget single-pass, passive and grammar-matched baselines. Require later behavior to change because of prior feedback, not simply repeated fixture correctness. Preserve original goal and event receipts. Record exact source SHA, elapsed budget, outcomes, failure cases and evaluator independence.

**HOURLY COGNITIVE SIMULATION NOT RUN.** This connector-only investigation did not execute Python Core or a held-out evaluator. Specific wiring defect: the default GoalCycle lacks a registered `run_experiment` capability. This is a research-only handoff, not learning, AGI, or consciousness evidence. No private runtime, employer or customer data included.

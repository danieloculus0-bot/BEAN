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

## Later source reconciliation (November 16, 2026)

The earlier deficiency statement above is **superseded by a newer source inspection**. The current `bean_run.py` registers `run_experiment` into the existing GoalCycle **after** constructing `NativeReasoningService`, conditional on native reasoning being enabled. The registered callable is `make_local_reasoning_experiment(native_reasoning_service)` from `bean/runtime/digital_experiment.py`. Thus it is incorrect to continue describing the current default reasoning-enabled runtime as having only two capabilities. With reasoning disabled, the experiment action remains unavailable. The previous paragraph is retained as historical evidence, not current status.

The adapter enforces a typed `native_reason_local` schema, bounded inputs and outputs, calls the existing `reason_local` method, and records a prediction digest. Even with an optional host evaluator, it returns `unverified` and `independent_outcome_verified: false`; a host-provided expected answer is not independent ground truth. Existing `bean/tests/test_digital_experiment.py` includes synthetic adapter, evaluator, and GoalCycle restart tests. **These tests were inspected as source, not executed in this reconciliation.** No evidence of independent held-out improvement or a complete adaptive multi-step Core cycle was established here.

Current public-safe manifest inspected: generation **56**, 56 boots, 1876 events, source SHA `ea9db993e4ac034e02831ea1f0ac44b25878622c`, Action `43948485531`. Candidate, passive and grammar-matched controls each scored **144/144**, so no measured advantage over strong controls. The manifest reports synthetic-only scope and `independently_audited: false`. Hosted BEAN adapter status reported revision `163f3e2815c4d6944345a0af78ae3e932041fdd3`, not the Python Core. Current source was read through authenticated GitHub; live Core execution and exact-head CI were not reproduced.

**Next falsifiable deficiency:** an independent held-out evaluator with a verified task oracle and delayed feedback must drive a later changed choice after restart. Compare the same tasks, seeds, and action budget against single-pass, passive, and grammar-matched controls; retain abstentions, incorrect predictions, evidence hashes and negative results. Do not treat the existing optional evaluator receipt as an independent audit. No new memory backend is warranted.

**HOURLY COGNITIVE SIMULATION NOT RUN.** No checked-out Python Core runner was accessible in this investigation; an attempted direct public Git clone failed due to DNS resolution of github.com. GitHub source reads were available, but do not constitute Core execution. The next execution requirement is an accessible checkout/CI runner with an independent held-out oracle and feedback-to-later-goal test.

# Default GoalCycle digital experiment wiring: source-level negative finding (2026-11-15)

BEAN CONTEXT ACK v1

- Base main SHA: `26c20133313c17df9910a87a90596188cf207ae8` (PR #387 merge). This note is a source inspection, **not** a runtime experiment or independent performance audit.
- Gatekeeper and origin: inspected `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, canonical origin and goal workstream, plus `research/github_brain/GOAL_REPETITION_2026-11-15.md`.
- Existing assets: `bean/runtime/goal_cycle.py` (SQLite action receipts and restart handling); `bean/runtime/digital_experiment.py` (bounded `make_local_reasoning_experiment` adapter, optional post-prediction evaluator); `bean/cognition/goal_state.py` (structured experiment proposal and persisted identity); `bean/tests/test_goal_cycle.py` (synthetic action injection).
- Continuity: `research/github_brain/manifest.json` at blob `0d7025df582d15623eb64821892ade3636d0d1b5` reports generation 51, 51 boots, 1,706 events, 144/144 candidate and grammar-matched correct. This does **not** establish learning advantage. The manifest reports source `544d7c42e0e14109dc3cb69a7d4f233328336c5b` and run 43698084471; this note did not independently replay the checkpoint.
- Hosted BEAN status and older recall were consulted. Its JavaScript adapter is not Python Core; evidence heuristics are not source authentication.
- Accessible owner repository inventory: 24 names returned, including BEAN and BEAN-AI-Bridge-. No private contents included.
- Current CI: exact-head workflows for this note are **Unknown** until PR CI runs. Historical green tests are not reused as proof.

## Deficiency observed in actual main source

`bean_run.py` constructs the default `GoalCycle` with only `update_models` and `run_reflection`. It does **not** register `run_experiment`. Meanwhile, `GoalStateEngine.propose()` can persist structured `run_experiment` proposals. The `GoalCycle._claim()` query only considers registered actions, so these proposals remain pending in the default runtime. The existing `test_real_registered_digital_experiment` registers a synthetic lambda in its own test, not the default application wiring.

PR #387 adds a bounded, evaluator-capable adapter in `bean/runtime/digital_experiment.py`; do not recreate it. The missing step is verified **registration and integration**, not another brain, storage backend or evaluator abstraction.

## Competing approaches and falsifiers

1. **Reuse the existing adapter in the default GoalCycle**, only after confirming a fully initialized `NativeReasoningService` is available and the host's experiment capability is explicitly enabled. Advantage: native reasoning, original SQLite and original receipts. Falsifier: a structured experiment stays pending despite the enabled host, a restart repeats a completed action, or the action returns success solely because its answer matches caller-provided expected output.
2. **Opt-in experiment action registration** after the native reasoning service is initialized, with no default execution. Advantage: isolates lifecycle and avoids accidentally treating expected output as ground truth. Falsifier: the opt-in configuration never reaches the normal tick scheduler, loses source/evaluator receipts, or bypasses persistent GoalCycle claims.

Choose only after inspecting `bean_run.py` lifecycle, `NativeReasoningService` initialization and `build_default_handlers`. Preserve the post-prediction oracle's `independently_audited=False` distinction. No untrusted code execution, device control or private data.

## Minimum executable acceptance test for next code increment

Use disposable synthetic SQLite and an actual native reasoning service. Create a fresh withheld structured question; record baseline with the default two-action registry; enable the bounded adapter and run the normal tick scheduler; inspect proposal, action decision, native reasoning journal, evaluator receipt and GoalCycle result hash. Close/reopen the DB and prove no repeated effect. Include mismatched expected answer, absent evaluator, invalid capability, evaluator exception, negative control and two distinct withheld domains. Compare candidate with equal-budget single-pass and memory-ablated controls. Record source SHA, seed, elapsed/call budget, failure cases and exact CI run IDs.

**HOURLY COGNITIVE SIMULATION NOT RUN**: this run had authenticated GitHub source access but no checked-out Python Core runner or network-capable checkout. Specific blocker: the default `bean_run.py` does not wire the existing bounded digital experiment action into its GoalCycle. No execution gain, model training, independent feedback or consciousness result is claimed.

Next action: inspect service initialization order and implement the smallest safe host registration plus an actual end-to-end restart/negative-control test. Do not repeat PR #372 or #387.

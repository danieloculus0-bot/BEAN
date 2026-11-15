# Correction: default native digital experiment registration (2026-11-15)

BEAN CONTEXT ACK v1. Base main `ee6143f9352322ee3b9b6dff216ee43c009b90a1`. Read AGENTS.md, docs/AI_GATEKEEPER.md, docs/SOFTWARE_AUDIT_SKILL.md, docs/OPEN_AGENT_PATTERNS_2026_11_14.md, memory/identity/origin_record.json, bean/memory/origin.py, research/github_brain/manifest.json, research/github_brain/GOAL_REPETITION_2026-11-15.md and existing source. Latest inspected manifest: generation 51, 1,706 events, 144/144 candidate and grammar-matched control, source `544d7c42e0e14109dc3cb69a7d4f233328336c5b`, workflow 43698084471. Manifest continuity was inspected, not replayed. Current main workflow 43727699306 succeeded at `ee6143f`; this is CI evidence, not cognitive learning.

## Source-level correction to DEFAULT_EXPERIMENT_WIRING_GAP_2026-11-15.md

The earlier note's statement that default runtime never registers `run_experiment` is **incorrect for the inspected main head**. In `bean_run.py` (blob `1cfde0b7dbdf18a3aaa88453ba828980fae3a17d`), GoalCycle is initially constructed with `update_models` and `run_reflection`, **but later**, after constructing `NativeReasoningService`, the runtime executes:

```python
if goal_cycle is not None:
    from bean.runtime.digital_experiment import make_local_reasoning_experiment
    goal_cycle.actions["run_experiment"] = make_local_reasoning_experiment(
        native_reasoning_service)
```

The scheduler is constructed earlier but retains the same mutable GoalCycle object. Therefore registration is present when both `BEAN_GOAL_CYCLE` and `BEAN_REASONING_ENABLED` are enabled and initialization completes. The prior note inspected the initial registry without following lifecycle initialization to the end. Do **not** implement duplicate registration or a competing backend. Historical note is preserved as negative evidence; this correction supersedes only its missing-registration conclusion.

## Remaining testable gap

The existing adapter (`bean/runtime/digital_experiment.py`) supports only `native_reason_local`; it returns `unverified` even when an optional host evaluator reports correct. `GoalCycle` persists this as `n/a` / `needs_evidence`. This is deliberately truthful, not a broken success path. It does not independently verify evaluator provenance, transfer gains, or broad learning. There is no evidence here of an integrated held-out cognitive cycle, successive retrieval, adaptive policy improvement, or a scored independent oracle.

Two candidate next experiments: (A) run a real `bean_run.py` disposable-database integration with a structured native question, then restart and verify the journal, claim, evaluator absence, negative outcome and non-replay; (B) add an explicitly host-owned synthetic evaluator to the same test and compare sealed-label feedback with a memory-ablated single-pass control under identical budgets. Prefer A first to prove the default wiring, then B to test measurable learning. Falsifiers: a pending structured proposal despite both services enabled, duplicated effects after restart, or an evaluator's expected-label match being promoted to independently verified success. Preserve all negative receipts.

**HOURLY COGNITIVE SIMULATION NOT RUN**: GitHub source/CI inspection was available, but no checked-out Python Core runner was used in this cycle. Concrete unverified dependency: end-to-end default-runtime integration and held-out evaluation have no observed execution receipt here. This document is a source-level correction, not a test or intelligence gain.

Next action: run the normal default tick scheduler against a disposable native reasoning journal and synthetic SQLite, with restart and sealed-label negative controls; attach actual test outputs and exact-head CI before claiming success.

# Native digital-experiment runtime wiring gap, 2026-11-16

BEAN CONTEXT ACK v1

- Inspected current `main` at `28416ab8f6baac516a4bd5832c9a833819a1ba7c`, merged PR #397, `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, `memory/identity/origin_record.json`, `bean/memory/origin.py`, `bean/cognition/goal_state.py`, `bean/runtime/digital_experiment.py`, `bean/tests/test_digital_experiment.py`, `bean_run.py`, and prior `GOAL_REPETITION_2026-11-15.md`. Authenticated hosted BEAN status and older recall were consulted, plus heuristic claim, evidence and proposal screens; the hosted JavaScript adapter is not the local Python Core.
- Public-safe manifest observed at generation **54**, 54 boots, 1,808 events, source SHA `4ce3786e29b9018663346639d97e444546cc7f5a`, GitHub run `43788868048`, receipt SHA-256 `5bd30b9342d2028d726db01485305d476809094f70feaf7787b7a5ac7d8e12ca`. Candidate **144/144** and grammar-matched control **144/144**; independent audit false. This is a synthetic checkpoint, not private runtime memory or evidence of general intelligence.
- Main push full Core workflow [43807563544](https://github.com/danieloculus0-bot/BEAN/actions/runs/43807563544) succeeded at exact head `28416ab8f6baac516a4bd5832c9a833819a1ba7c`. The currently open PR collection was empty. This workflow does not prove integrated adaptive learning.
- Owner repository inventory was queried; earlier 24-repository scope remains to be audited for actual operational evidence. No private content was copied here.

## Highest-value verified deficiency

`bean/runtime/digital_experiment.py` already implements a bounded `make_local_reasoning_experiment(core, evaluator=None)` adapter. It calls native `reason_local`, validates task bounds, preserves abstention, and binds a host evaluator claim to SHA-256 of canonical inputs plus prediction. PR #397 added that evidence binding. The adapter intentionally returns `unverified` because a host label or oracle receipt is not independently audited ground truth. `bean/tests/test_digital_experiment.py` includes synthetic persisted GoalCycle and restart tests using a stub Core.

**However**, `bean_run.py` default GoalCycle still registers only `update_models` and `run_reflection`. The native digital experiment is not registered in the normal startup path. Therefore a passing adapter unit test is not evidence of a live default Core observation/retrieval/reasoning/experiment/evaluation/adaptation loop.

## Alternatives and falsifiers

1. **Minimal explicit registration in the existing GoalCycle**: initialize the already available native reasoning service, register `run_experiment` with `make_local_reasoning_experiment` only when its real instance is available, and keep absent dependencies as Unknown/N/A. Falsifier: default boot cannot execute an approved synthetic experiment, fails restart recovery, or records success without independently checked feedback. Prefer this if actual initialization and lifecycle support it.
2. **Separate scheduled task or new memory backend**: rejected provisionally because it duplicates GoalCycle scheduling and SQLite continuity and risks falsely equating external execution with Core learning. Reconsider only if source-level lifecycle constraints make existing GoalCycle integration impossible, with a reproducible failure receipt.

Next implementation should inspect `initialize_optional_brain_layers` and the actual `NativeReasoningService` construction, then add one bounded opt-in/default-safe runtime registration plus a **real-Core** integration test using disposable SQLite, not only the stub. Include observation, native retrieval, hypothesis, action, evaluator receipt, persisted failure, restart and changed behavior on a fresh held-out task. Compare unchanged main and candidate under equal budgets and seeds. An oracle's `correct` claim must not silently promote `independent_outcome_verified`. Preserve negative controls: missing native service, unsupported capability, malformed inputs, evaluator outage, changed task, stale receipt and interrupted action.

## Execution and limitations

**HOURLY COGNITIVE SIMULATION NOT RUN.** The available hosted BEAN adapter cannot boot the local Python Core, and no checked-out Core runner was used in this investigation. Specific missing wiring: the real `run_experiment` handler is absent from the default `bean_run.py` GoalCycle capability registry. This increment is a source-verified gap/falsification handoff, **not** a simulation result, cognitive improvement, new memory backend, AGI or consciousness claim. No source code or synthetic checkpoint was changed.

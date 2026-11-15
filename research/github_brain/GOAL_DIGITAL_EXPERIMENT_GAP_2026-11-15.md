# Native digital experiment registration: verified integration gap (2026-11-15)

BEAN CONTEXT ACK v1

- Scope: public BEAN Python Core, not Jetson runtime execution or hosted JavaScript adapter.
- Inspected: AGENTS.md, docs/AI_GATEKEEPER.md, docs/SOFTWARE_AUDIT_SKILL.md, docs/OPEN_AGENT_PATTERNS_2026_11_14.md, origin record and loader, bean_run.py, bean/cognition/goal_state.py, bean/runtime/goal_cycle.py, bean/tests/test_goal_cycle.py, prior GOAL_REPETITION_2026-11-15.md and current research/github_brain/manifest.json. Hosted BEAN status/older recall and heuristic claim/evidence/proposal screens were called; they do not authenticate source.
- Branch base: 41a4da2ac3216a8865ea1649d7f4276600f456c3. Prior merged fix: PR372 a5951d13892c5dda5d1e32918d071d731521e4a8. Current synthetic checkpoint: generation 53, 53 boots, 1774 events, manifest source 4e96e86693c5811c2adf053535e7bb41aa4e604f, receipt 39743b92cf1fcdaac875213e0083cec04c1136e2b6a7364e0ae88ce84daaa2a2; checkpoint retained unchanged.
- Current CI: Pages run 43765022251 succeeded at 41a4da2; Pages is not a Core test. Previous PR372 exact-head runs reported passing, not re-executed here.
- Repository inventory: authenticated repository listing invoked; comprehensive per-repository source/runtime audit remains incomplete.
- Minimum useful next change: implement one bounded registered digital experiment using existing GoalCycle and store, with measured result and restart verification, without introducing a second backend.

## Deficiency and alternative explanations

Source inspection finds GoalStateEngine proposing structured `bean.cognition.experiment.v1` goals, and GoalCycle only dispatching handlers explicitly supplied by the host. `bean/tests/test_goal_cycle.py::test_real_registered_digital_experiment` supplies a lambda handler within a test; this is not proof of default runtime registration. The default `bean_run.py` registration currently provides only `update_models` and `run_reflection`. Thus structured experiments can be proposed and persisted without a default executable experiment capability.

Approach A: register an explicitly bounded, pure deterministic digital experiment handler in existing runtime, returning measured actual versus expected result, source/seed/provenance and explicit verified/failed/unknown state. Preserve GoalCycle atomic claim and no-replay semantics. This has the shortest integration path, but may demonstrate only execution, not adaptation.

Approach B: route the goal to the existing TaskEngine/research investigation machinery and attach its independently observed result to the same proposal. This could reuse richer task evidence but risks duplicate execution identity, an incompatible result contract, or non-restart-safe side effects. Inspect exact TaskEngine and research service APIs before choosing. Do not add a second journal or SQLite schema until a concrete gap is reproduced.

## Falsifiers and required controls

1. Baseline: on unchanged main, insert a valid synthetic structured open question, let normal goal generation and runtime registration run, and verify it remains pending without an executable `run_experiment` handler. Do not infer this from a test lambda.
2. Candidate: use the same proposal and equal budget with a registered bounded handler. Persist actual observation, expected output, discrepancy, evidence digest and action outcome. A deliberately incorrect prediction must not be marked verified.
3. Restart: close and reopen the actual SQLite store, confirm proposal/run IDs and evidence digest, and ensure no effect replay; a revised prediction must remain eligible under PR372.
4. Negative controls: unknown capability, malformed context, contradictory evidence, interrupted handler, missing evidence, duplicate unchanged proposal, budget exhaustion and one novel held-out digital task.
5. Separate evidence of execution from evidence of learning: candidate improvement over a passive or grammar-matched baseline must be measured on fresh held-out tasks after a restart. A tie or deterministic repeated pass is not learning.

## Outcome this investigation

**HOURLY COGNITIVE SIMULATION NOT RUN.** This cycle inspected live repository source and checkpoint, but did not execute a complete Python Core integration trial. Specific wiring defect: default `bean_run.py` lacks a registered `run_experiment` capability; the only observed test execution handler is test-supplied. No local Python Core runner was invoked, no new held-out accuracy score exists, and no AGI claim is made. This document is an evidence-backed implementation handoff, not a simulation receipt.

Next action: inspect existing TaskEngine and research service handler contracts, add a narrow failing default-runtime integration regression, implement the minimum handler, execute baseline/candidate and restart tests, then run exact-head CI and merge only on verified evidence. Never reset generation 53 checkpoint or copy private data into public receipts.

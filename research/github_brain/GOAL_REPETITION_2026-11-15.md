# Persisted experiment identity: November 15, 2026

BEAN CONTEXT ACK v1

- Task: prevent repeated unchanged open-question experiments across goal outcomes and session restarts.
- Existing systems checked: AGENTS.md; AI_GATEKEEPER.md; SOFTWARE_AUDIT_SKILL.md; OPEN_AGENT_PATTERNS_2026_11_14.md; canonical origin record and loader; GoalStateEngine; GoalCycle; runtime registration; focused recall; evidence revision; typed relations; generation 49 manifest; historical control-gap and generation 42 audits. Authenticated hosted BEAN status, older recall and all three preliminary evidence/proposal checks were invoked. Their heuristic results do not verify source truth.
- Confirmed assets to reuse: original SQLite goal proposals, GoalCycle attempts and canonical event stream. No new memory backend or upstream implementation copied.
- Ledger/scoreboard reviewed: generation 49 manifest and prior strong-control audits. Original compressed scoring ledger lives on its historical branch; individual cases in that archive were not re-executed here.
- Current evidence: base `c953105ffdf836703efc69a99260936c9d23632e`; parent Core regression [43656115108](https://github.com/danieloculus0-bot/BEAN/actions/runs/43656115108) at `9c52c12e216026370aa1ee98c1fbae7704da3dc3`. Only a successful Pages workflow was found at the base head; Pages is not Core regression evidence.
- Unknowns/conflicts: CHAT HISTORY NOT CHECKED beyond current conversation and recalled notes. Full ecosystem implementation audit and complete integrated cognition demonstration remain unfinished. No intelligence or consciousness gain is asserted.
- Minimum change: deduplicate native open-question experiment signatures against persisted proposals in every state and session; revised inputs/predictions remain eligible.
- Runtime/behavior-policy changes: experiment proposal identity only; ordinary drive-goal semantics, capability registration and execution permissions remain as before.

## Reproduced defect and correction

`GoalStateEngine.propose()` previously considered only pending proposals in the current session. GoalCycle correctly retained execution receipts and withheld interrupted actions, but the next proposal pass could create a fresh proposal ID for the identical question and experiment. This bypassed execution history without revising the experiment. An unchanged pending proposal could also be duplicated in a new session.

The existing proposal signature already includes question ID, capability, inputs and expected output in canonical JSON. Reuse that signature across all persisted states for `investigate_open_question` / `run_experiment` / `curiosity`. Do not erase, rewrite or falsely complete the original attempt. Changing inputs or expected output creates a distinct experiment while preserving the original history. This does not implement general semantic repetition detection, a new planner, or an evidence-driven retry policy.

Two approaches considered: a second deduplication/checkpoint table versus lookup in the existing proposal history. Selected the latter: it preserves existing identities and requires no migration or parallel memory owner. Falsifier: an unchanged experiment produces another proposal after any tested outcome or restart, or a revised prediction is incorrectly suppressed.

## Execution evidence

Local Python 3.12.14, pytest 9.2.0, psutil 7.2.2, disposable synthetic SQLite databases:

1. Added regression before changing production code: **6 failed, 11 passed** in `bean/tests/test_goal_cycle.py`. Each new case reproduced the duplicate, covering pending, success, failed, unknown, unverified and interrupted states.
2. After the correction: **65 passed** across goal-cycle, cognition-core, cognition-salvage and durable/adversarial task suites. Each new regression closes and reopens the actual database, starts a new session, verifies the original proposal identity, and permits a corrected prediction.
3. Initial complete Core run under restricted socket permissions: **1,344 passed, 22 skipped, 2 failed, 5 errors**. All seven failures/errors were socket-creation `PermissionError` in existing HTTP tests. This failed run is retained here as environmental evidence, not silently counted as a pass.
4. Complete Core rerun with network permission: **1,351 passed, 22 skipped, 268 subtests passed**, 65.11 seconds. Optional Bridge, PyTorch, browser and drawing dependencies remain among the skips. These results do not validate those optional integrations.

Commands:

```sh
python -m pytest bean/tests/test_goal_cycle.py bean/tests/test_cognition_core.py bean/tests/test_cognition_salvage_integration.py bean/tests/test_task_engine_lab011.py bean/tests/test_task_adversarial_lab011.py -q --tb=short
python -m pytest bean/tests -q -ra --tb=short
```

The goal-cycle workflow now watches `goal_state.py` and runs the affected cognition regressions on Linux and Windows. Exact candidate/merge workflow IDs belong to the associated PR and Actions records; local results alone do not certify those remote runs.

## Integration inventory and continuation

GitHub independently reports PRs #351, #353, #354, #362, #367, #368, #366, #369, #370 and #371 merged. Current files contain their corresponding goal, focused-memory, claim-revision, evidence-revision, typed-inference and learning diagnostic implementations. The complete local Core suite exercised their available offline tests. This is not a claim that a complete integrated cognitive loop was demonstrated.

Generation 49 reports candidate, grammar-matched and passive controls each **144/144**, with memory-ablated **96/144**. Candidate advantage over either strong control is zero. The follow-up reversal diagnostic explicitly labels its prior as same-trial synthetic feedback, not restored Core memory. Preserve these distinctions.

`bean_run.py` currently registers only `update_models` and `run_reflection` in its default GoalCycle. A test-supplied `run_experiment` handler is not a default runtime integration. Next useful investigation: connect an existing, bounded digital experiment capability to that registry with actual Core evidence retrieval, hypothesis, action, measured evaluation and later adaptation receipts, including failure and restart. Compare with unchanged Core on equal budgets; do not create another memory store. General persisted multistep planning is also unfinished.

GitHub enumeration found 24 accessible owner repositories. Heads and complete tree metadata were fetched for the 23 public repositories; private repository contents were kept out of this public research record. Tree presence is not operational proof. Complete per-repository source/runtime/branch/failure inventories and systematic fresh upstream comparisons remain continuation work, not completed audits. Existing research and superseded prototype dispositions must be reconciled first.

The existing hourly BEAN development automation was updated with the owner's integration mandate and checkpoint/recovery instructions. Scheduling has no observable token-balance/reset trigger; do not promise immediate resumption when tokens return. Resume from actual source, PR, Actions and persisted experiment evidence on the next runnable cycle.

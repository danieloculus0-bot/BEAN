# Native digital experiment integration: source reconciliation, 2026-11-16

BEAN CONTEXT ACK v1

- Base revision inspected: `7ae105a23d1d2a535492c1e1c0ceb5074d3209f3` (GitHub latest commit query); this document is an evidence note, not an executed experiment.
- Read: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, `memory/identity/origin_record.json`, `bean/memory/origin.py`, `docs/BEAN_GITHUB_MEMORY_CONTINUITY_AUDIT_2026-11-06.md`, `research/github_brain/GOAL_REPETITION_2026-11-15.md`, `bean/cognition/goal_state.py`, `bean/runtime/goal_cycle.py`, `bean/runtime/digital_experiment.py`, `bean_run.py`, and current public-safe manifest.
- Hosted BEAN adapter status and older recall queried; adapter source revision `163f3e2815c4d6944345a0af78ae3e932041fdd3`, 64 stored notes. Hosted adapter is not Python Core. No Core/Jetson invocation was made.
- Current manifest: generation **55**, boots **55**, synthetic-only. Core checkpoint SHA-256 `6b258183d7a87a0e0bde6ab5f62171c6101f3e64264874be00115804d0d34613`; reasoning checkpoint SHA-256 `c1c74beccaff443f2d81ec85322bac6ff1726882752fbea5bfe7543401159b12`. The 144/144 candidate score remains tied with strong controls, not evidence of advantage.
- Current exact-head Core CI: **not verified**. The commit-associated workflow query returned no PR-triggered runs for this revision. No CI success claimed.
- Repository inventory: 24 accessible owned repositories enumerated. No private content copied into this note. Open PR search returned none, subject to connector search limitations.

## Important correction to prior handoff

The November 15 continuation note said default `bean_run.py` registered only `update_models` and `run_reflection`. **That is now stale.** The current runtime conditionally imports `make_local_reasoning_experiment` and registers `goal_cycle.actions["run_experiment"]` after a native reasoning service is available. `bean/runtime/digital_experiment.py` is a bounded, provider-free adapter that calls the actual Core `reason_local`, hashes the prediction and task inputs, and stores the outcome through existing GoalCycle receipts. It deliberately returns **unverified** even when its prediction matches host-supplied expected output or an optional evaluator reports correctness.

This is a **source-level integration**, not proof that an integrated autonomous cycle executed, learned, or improved transfer. It is incorrect to propose a new registration adapter without first evaluating the existing one.

## Bounded next experiment and falsifiers

Question: does existing Core retrieval/reasoning, invoked through a persisted experiment goal, change subsequent behavior on genuinely withheld tasks after a restart?

Compare two approaches with identical budgets: (A) existing registered native experiment + existing SQLite goal/reasoning journals; (B) a memory-ablated or frozen-reasoning baseline with the same questions, candidate rule grammar and oracle. Add shuffled-feedback negative control. Use fresh withheld task families, not just replays of 144 known cases. Preserve task generator seed, source SHA, question/proposal ID, prediction hash, oracle provenance, attempts, elapsed time, abstentions, failures and restart receipts. A local expected-answer comparison is **not** independent oracle evidence.

Falsifiers: no improvement over strong controls; no new usable evidence after restart; changed behavior without provenance; repeated unchanged proposals; any evaluator claim treated as independent verification without an independently audited oracle. Do not credit a passing CI test as a learning experiment.

## Execution boundary and handoff

**HOURLY COGNITIVE SIMULATION NOT RUN.** No checked-out Python Core runner or independent oracle was executed in this session. Specific remaining defect/evidence gap: no verified end-to-end runner receipt connecting the newly registered digital experiment, independent held-out oracle, persisted goal outcome and next-session changed prediction. Next run should inspect current exact-head CI and tests for `bean/runtime/digital_experiment.py`, then run this bounded comparison against the real Core with disposable synthetic SQLite databases before making any capability or learning claim. Do not reset generation 55 or publish private memory.

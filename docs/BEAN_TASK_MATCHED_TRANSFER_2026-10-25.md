# BEAN task-matched transfer: evaluation must use the same context as decisions

**Scope:** isolated Lab026 native-skills research branch stacked on [PR #144](https://github.com/danieloculus0-bot/BEAN/pull/144). It does **not** modify the neural Q-learning engine, live AIscend execution or the hosted BEAN notes connector.

## Problem

The previous `BEANReasoningSkills.decide` used same-domain **task-lexical retrieval** of lessons, while `run_paired_trial` evaluated the first three lessons from the selected domain, regardless of the task. A positive matched-trial score could therefore certify a context different from what the actual BEAN decision interface would use. A passing selector plus stored context is not enough to prove behavior change.

## Minimal correction

- Centralize the deterministic source-linked per-strategy task retrieval in `bean.learning.experimental.task_lesson_matches`.
- `BEANReasoningSkills.recall` and the task-aware Lab026 trials now use exactly the same ranking, token match and ordering; `adaptive` evaluation carries forward the query after frozen selection.
- Each trial records `context_policy` and the SHA-256 of exactly the evaluated context. Unmatched tasks do not borrow unrelated same-domain lessons.
- Existing older generic Lab026 trials remain explicitly `legacy_domain_first_three`; task-aware trials are opt-in at the lower-level API and are used by the native BEAN decision and holdout interfaces.
- Only the public question enters retrieval. The held-out target is consumed by the independent judge after the model returns; it is never passed to the retriever.

## Acceptance tests

Use `python -m unittest bean.tests.test_native_reasoning_skills -v`, followed by the existing Lab026 suite and all Core tests in the existing Windows/Ubuntu workflow.

The new deterministic **synthetic** contract constructs an irrelevant same-domain lesson before the correct lesson. The selection evaluation must ignore the decoy and choose the same source IDs actually returned by `decide`. It checks exact context hash equality, cold vs placebo vs adaptive comparisons on task-disjoint questions, repeatable source-linked selection after SQLite restart and rejection of unrelated task matches. Source lessons include unverified host outcomes, and the fixture model is explicitly not a real reasoning model.

**Falsification:** a selected arm earns no transfer credit if it passes under a different retrieval path, accesses an expected answer through its context, fails the cold/placebo comparison, or cannot recover its decision source after restart. A passing synthetic fixture means the *mechanism* works, not that general real-task learning has occurred. Genuine evidence requires a frozen, independently evaluated set of tasks with a real inference provider, grounded outcome receipts, and post-restart improvements.

## Evidence boundary

This is context-selection parity and synthetic task-family transfer, **not** general semantic understanding, neural weight improvement, self-directed learning or independently demonstrated out-of-distribution intelligence. Preserve all failures and exact CI commit SHA. Do not promote this PR directly to Core main without reconciling the parent research branch and validating current Core regressions.

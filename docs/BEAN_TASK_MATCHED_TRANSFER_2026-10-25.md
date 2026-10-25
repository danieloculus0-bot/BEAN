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

## Holdout leakage correction (2026-10-25)

A further code review found a genuine error: `BEANReasoningSkills.evaluate_holdout` was still invoking `run_paired_trial` without `task_aware=True`. Consequently the development selection and final held-out evaluation were **not actually using the same retrieval path**, despite the original task-time tests passing. This revision corrects the call and adds a direct held-out `context_sha256` equality assertion against actual adaptive decision material.

Each evaluated public question now receives a stable SHA-256 fingerprint of NFKC-normalized, case-folded, whitespace-normalized text. The holdout rejects prompts repeated within the holdout or seen in any prior recorded trial, even if the task ID or letter case changes. Older trials without fingerprints cannot certify novelty and are rejected rather than quietly accepted. This guards against a common false positive; it does not prove that semantically paraphrased questions are independent, nor that a real model was never trained on these tasks.

No expected answer enters the retrieval query or the normalized public-question fingerprint. Counterexamples and failures remain in the append-only BEAN journal.

## Acceptance tests

Use `python -m unittest bean.tests.test_native_reasoning_skills -v`, followed by the existing Lab026 suite and all Core tests in the existing Windows/Ubuntu workflow.

The new deterministic **synthetic** contract constructs an irrelevant same-domain lesson before the correct lesson. The selection evaluation must ignore the decoy and choose the same source IDs actually returned by `decide`. It checks exact context hash equality, cold vs placebo vs adaptive comparisons on task-disjoint questions, repeatable source-linked selection after SQLite restart and rejection of unrelated task matches. Source lessons include unverified host outcomes, and the fixture model is explicitly not a real reasoning model.

**Falsification:** a selected arm earns no transfer credit if it passes under a different retrieval path, accesses an expected answer through its context, fails the cold/placebo comparison, or cannot recover its decision source after restart. A passing synthetic fixture means the *mechanism* works, not that general real-task learning has occurred. Genuine evidence requires a frozen, independently evaluated set of tasks with a real inference provider, grounded outcome receipts, and post-restart improvements.

## Evidence boundary

This is context-selection parity and synthetic task-family transfer, **not** general semantic understanding, neural weight improvement, self-directed learning or independently demonstrated out-of-distribution intelligence. Preserve all failures and exact CI commit SHA. Do not promote this PR directly to Core main without reconciling the parent research branch and validating current Core regressions.


## Bounded actual reasoning-model trial (2026-10-25)

The new research-only `bean.evaluation.live_reasoning_transfer` targets **`gpt-6.1-sol`, medium reasoning effort**, via the Responses API, with an upper budget of 18 provider calls (no automatic retries, tool execution, funds access, or trading). The API credential is read exclusively from `OPENAI_API_KEY` on the GitHub Actions runner; neither the token nor raw HTTP failure body is logged. A missing credential produces `blocked_no_api_key` and a failing live-job gate, **not** a simulated pass.

The same fixed model is evaluated on an artificial ASTER-7 dispatch-key protocol. A development cold answer is measured first; BEAN only writes a reflection if the answer fails. A separate actual development response must correctly follow the documented general rule before BEAN may retain it as a successful reusable skill. Then BEAN's existing selection chooses among real-model cold, irrelevant-placebo, reflection, skill, and instruction arms on development cases. The SQLite ExperienceBank is closed and reopened before evaluating fresh task IDs and different token instances using the frozen winner. Expected answers are supplied only to a strict deterministic judge; none enter the provider's input.

The output includes model response IDs, served model ID, every raw public-task answer, pass/fail records, complete selection and held-out scores, full source-linked state and the append-only experiment journal. Both real-provider and transport/credential failure statuses are preserved in workflow artifacts. Old evaluations with different prompts may not be credited as independent new samples.

**Crucial limitation:** This is a *real reasoning model performing controlled, invented tasks with evaluator-supplied feedback*, not proof of spontaneously discovered rules or transfer to real engineering/financial problems. A correct BEAN-memory answer tests experience retrieval and application to different instances of one task family. Real generalization to unseen domains would require independent external tasks and separately sourced reward observations, not this synthetic-domain test alone. If the baseline already answers correctly, the experiment is inconclusive and deliberately refuses to manufacture a development mistake.

Verification: `python -m unittest bean.tests.test_live_reasoning_transfer -v` (offline structural fixture, not live evidence), then inspect the actual `BEAN real reasoning model learning transfer` GitHub Actions run and `bean-real-reasoning-matched-trial` artifact at the exact tested commit.


## Actual provider status and free reasoning comparison

At [GitHub run 40206569071](https://github.com/danieloculus0-bot/BEAN/actions/runs/40206569071), the GPT-6.1 Sol research harness passed its Ubuntu and Windows **offline contracts**, but the actual-provider job failed with `blocked_no_api_key` because `OPENAI_API_KEY` was empty. **Zero GPT-6.1 Sol requests occurred.** Do not count this as a reasoning-model experiment, and do not say the BEAN experiment passed.

A separate [pinned zero-token-price NVIDIA Nemotron 3 Ultra model](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b%3Afree) was selected as the available fallback. A prior [October 11 OpenRouter trial](https://github.com/danieloculus0-bot/BEAN/actions/runs/38152611734) had a credential and attempted one request, but was rate limited with HTTP 429 and never returned a model candidate. The new [`BEAN free pinned reasoning model transfer` workflow](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-free-reasoning-transfer.yml) uses `OPENROUTER_API_KEY` only for synthetic public tasks, pins the `nvidia/nemotron-3-ultra-550b-a55b:free` model, hard-caps at 18 requests and captures independent real responses or an explicit blocker. There is no paid-provider fallback.

The free model is an alternate real reasoning provider, **not GPT-6.1 Sol**. Its scores must remain separately identified by model and run. An HTTP/rate-limit failure or missing response is not an evaluated task, and cannot establish learning.


## Verified first actual reasoning-model transfer run

**Execution:** [GitHub Actions run 40206850819](https://github.com/danieloculus0-bot/BEAN/actions/runs/40206850819) on exact experiment commit `4128b5c1e0c51262efc749e8930a28b97fe287c9`. Both offline provider contract and live provider job succeeded. Model requested **and actually served** was `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter. 18 real model responses were recorded, and raw answers, matched pass/fail decisions and BEAN's SQLite experience ledger are retained in [GitHub artifact 12604240520](https://github.com/danieloculus0-bot/BEAN/actions/runs/40206850819/artifacts/12604240520) (90-day Actions retention).

**Development selection:** frozen selector chose the **reflection** lesson, scoring 2/2 on its two selection tasks. Its skill and prompt alternatives also scored 2/2; both cold and irrelevant-placebo arms scored **0/2**. These are genuine model replies, not fake-model fixture scores.

**Post-restart holdout:** Two different tag instances of the invented ASTER-7 dispatch-key problem were evaluated with the selection frozen after SQLite close/reopen. The real model answered correctly **2/2 with BEAN's retained reflection** and **0/2 cold, 0/2 irrelevant placebo**. The selection identity was identical after restart. Observed incremental success was +2 of 2 matched held-out examples relative to each control.

**What this demonstrates:** BEAN's existing journal can retain evaluator-grounded feedback, select and retrieve the appropriate reflection, survive restart, and measurably improve a real reasoning model on unseen *instances of the same fictional rule*. These are actual provider responses and actual judgment receipts, not simulated-network placeholders.

**What this does not demonstrate:** The general rule was supplied by the evaluator after the model made a real development-period error; BEAN did not autonomously invent the rule. Test labels and the fictional task family were authored inside the same experiment, not independently commissioned. Only 2 held-out examples, one real model, one selected rule and one run were tested. There are no changed model weights, cross-domain generalization results, independently blind real-world validation or crypto returns. Confidence intervals, multi-model tests, independent rule discovery and robustness to paraphrased tasks remain to be assessed. Do **not** promote this small result to a claim of general BEAN cognition.

The default preferred `gpt-6.1-sol` model **was not tested** because the runner lacked `OPENAI_API_KEY`, as documented above. Do not merge or auto-enable live trading from this result.

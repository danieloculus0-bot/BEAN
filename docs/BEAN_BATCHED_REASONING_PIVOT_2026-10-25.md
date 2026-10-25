# BEAN native reasoning pivot: owned learning loop, replaceable inference, compressed trials

Status: **research only**, stacked on PR #168 and #167. BEAN itself owns memory, reasoning-policy selection, evidence, feedback, retrieval and decision packets. NVIDIA Nemotron is a **replaceable reasoning engine**, not BEAN's identity, historical memory or verified outcome oracle. The local DQN remains a separate, optional optimizer; Q-learning weights are not proof that BEAN reasons better.

## The real signal and why the pivot matters

Original [Nemotron run 40206850819](https://github.com/danieloculus0-bot/BEAN/actions/runs/40206850819) confirmed 2/2 held-out correct with a human-provided procedural lesson, against 0/2 cold and placebo; it did **not** show independent rule induction.

The harder [PR #168 study](https://github.com/danieloculus0-bot/BEAN/pull/168) required a model to infer ORCHID-7's rule from examples. Real partial [run 40212952629](https://github.com/danieloculus0-bot/BEAN/actions/runs/40212952629) preserved **13 real inference calls** before OpenRouter HTTP 429. The model produced the correct ordering rule and passed a separate development validation. BEAN's measured *selection* chose **raw input/output examples**, not its model-authored reflection: cold 0/2; placebo 0/2; reflection 0/2; reusable skill 1/2; example-based prompt 2/2. These are DEVELOPMENT scores, not finished holdout proof.

Partial [run 40212932438](https://github.com/danieloculus0-bot/BEAN/actions/runs/40212932438) made 15 calls and selected the reusable skill (cold/placebo were both 0/2). It also stopped at HTTP 429. Never average independent partial runs as if they were matched holdouts. Their original ZIP artifacts and rejected/verbose answers remain available through GitHub Actions.

This is the central design finding: a strong reasoning provider may generate a flawed explanation but still solve new cases using observed examples. **BEAN, not the model, should compare different remembered reasoning representations and reuse whichever passes controlled tests.** We are retaining the existing ExperienceBank, matching selector, holdout protections and SHA journal, not importing a second black-box memory service.

## Compression without mixing experimental conditions

Previous protocol: 25 model calls per task family, including 10 development selection and 12 holdout calls. Across two families, **50 potential calls**. New protocol preserves each exact case and answer but **batches questions inside each control arm**, never across different arms:

| Phase per family | Previous calls | Compressed calls |
| --- | ---: | ---: |
| Cold development error, model-written lesson, independent development validation | 3 | 3 |
| Development selection: 2 questions x 5 isolated arms | 10 | 5 |
| Frozen holdout after SQLite restart: 4 questions x 3 isolated arms | 12 | 3 |
| **Total** | **25** | **11** |

Two families fall from at most **50 to 22 provider requests (56% fewer)**, conditional on earlier phases actually proceeding. This is a calculation of **request count**, not a measured 56% token reduction. Question contexts are no longer wastefully right-padded to 800 characters, and a compact JSON answer is requested. Actual token totals, latency, malformed outputs and rate limits must be measured from real provider usage, not guessed.

`bean.learning.batched_trials.run_batched_paired_trial` now offers this mechanism inside BEAN's own learning package. `BEANReasoningSkills.evaluate_and_select(..., batched=True)` and `evaluate_holdout(..., batched=True)` reuse the original source-backed journal and selected strategy. Every case still has its own task ID, question hash, context hash, answer hash and Boolean judgment. One call never receives cold and adaptive contexts simultaneously. Malformed provider JSON is recorded verbatim and scored wrong on all affected cases, not silently treated as a success.

## Three-call recovery before new training

A new stage downloads the exact preserved source artifact **12606531457** from original run **40212952629**, verifies SHA-256 for the original `report.json`, `experience.sqlite3`, and `provider_calls.jsonl`, restores BEAN's *original frozen example-prompt selection*, and tests **four new ORCHID-7 tag combinations** never used in any prior experiment. It does **not** spend more tokens repeating the original 13 calls or reselect based on holdout results. Its fresh holdout consumes at most **three** provider requests: one cold batch, one unrelated-memory batch and one BEAN-memory batch.

Original partial holdout questions were already sent to the model before rate limiting, so **we explicitly use new unseen questions** instead of presenting repeated questions as new independent evidence.

Run `python -m unittest bean.tests.test_batched_trials bean.tests.test_nemotron_self_derived_transfer -v` and inspect the real-provider GitHub workflow and archived proof hashes. If HTTP 429 recurs, preserve `partial_failed` and every actually received response, do not retroactively credit or fabricate a score. Retain the source archive unchanged.

## What is hard-wired, and what is not

Hard-wired BEAN-owned components: task representation, evidence IDs, normalized source matching, compressed per-arm evaluation, signed outcome journal, selection logic, cold/placebo controls, restart and frozen evaluation, and explicit failure receipts.

Swappable boundary: model-specific inference request and response parsing. Nemotron is today's free reasoning provider. Future local weights or other APIs may plug into that boundary without wiping BEAN's memories.

Open gaps: original source task families are fictional and evaluator authored; the model learns from examples, not independently observed real-world outcomes. The latest source partial selection favored raw examples. Even successful resume would test only 4 held-out instances of one protocol. We still need independent problem families and recorded cross-domain improvements before a claim of generalized BEAN learning. **No production or live AIscend trading changes.**

# BEAN Lab021 — Three-domain, feedback-driven autonomy benchmark

**Status:** Isolated research branch, not a new production readiness claim.

We can only raise BEAN's demonstrated autonomy score when testing meaningfully
different skills, not by rerunning the same `clip_score` function.

## Protocol

The experimental agent receives *three unrelated* broken Python functions,
plus public specifications:

1. Merge half-open time windows, including zero-length, touching and invalid
   endpoints.
2. Resolve directed dependencies in deterministic lexicographic topological
   order, including implicit nodes and cycles.
3. Aggregate inventory events, strictly validating inputs, honoring first
   event IDs and preserving sorted SKU keys.

The model is provided **only the task specification and broken source**, not
the evaluator's source, fixtures, seeds, expected results or stack traces.

The workflow is autonomous once a run is initiated:

1. **Evaluator validity:** no secret. Verify that broken baselines fail and
   independently correct implementations pass both development and holdout
   tests. Reject risky Python syntax and malformed source.
2. **Model authoring:** exactly one `openrouter/free` call per task, max
   three total; no paid fallback. Save SHA256-addressed candidate modules.
   **Do not execute generated source in this job.**
3. **Independent feedback:** on a separate credential-free runner, evaluate
   against synthetic development cases and return only aggregate pass counts.
4. **Model revision:** automatically retry *only* unsolved tasks, at most one
   additional free-model request each, given previous overall score but no
   hidden test values. Save original and revised source separately.
5. **Final sealed evaluation:** use a fresh random seed that was not used in
   development. Evaluate baseline, first candidate and revised candidate
   separately; choose the revision **before**, never based on, holdout scores.
6. Archive model names, hashes, both candidate sets, both test reports, tests
   and negative outcomes as GitHub Actions artifacts.

## Why this is a stronger test

Different domains require interval reasoning, graph planning, and stateful
deduplication rather than numeric literal replacement. The explicit
feedback/retry loop makes this a *multi-step* source-improvement attempt.
The candidate grader runs code on an isolated disposable CI runner with no
OpenRouter key, not on the source-authoring host. It allows a limited set
of builtins and Python AST nodes and uses time-limited subprocesses. This is
**not** an operating-system-grade security sandbox, and arbitrary malicious
model output still requires stronger container isolation for untrusted
production environments.

The holdout seed is independent of development, but the oracle code remains
public in this research branch. It is **hidden from the prompt**, not
cryptographically secret. This evaluates unsupervised behavior with a
reasonably isolated grading contract, not undisclosed real-world tasks.

## Readiness gates

A qualitative autonomy score of 8/10 would require more than this experiment
alone: strong heldout results across several dissimilar tasks, evidence that
autonomous revision reliably improves on first attempts, persistent learning
that transfers across tasks and restarts, independently validated defect
discovery in existing unfamiliar software, and multiple clean runs.

Report:
- Baseline and model accuracy on truly held-out fixtures.
- How many tasks obtained a parseable model answer.
- Failed first attempts, failed revisions, regression rate.
- Model/provider availability, request count and code hashes.
- Whether generation, feedback, revision and independent validation all ran.

**Do not award points because a CI job completed.** A successful job may still
contain zero passing model-written solutions or unavailable providers.

Workflow: [BEAN LAB021 autonomy generalization](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-autonomy-transfer-lab021.yml).

# BEAN Lab 016 — Actual hosted LLM, simulated world only

**Scope:** No Jetson, robot hardware, devices, local model service, ERP, personal
conversation content, or real-world action. This uses GitHub Models' real
hosted inference endpoint from a one-shot GitHub Actions job and a disposable
fictional simulation.

## Purpose

Labs 014 and 015 demonstrated the simulated investigation plumbing with
scripted or non-neural providers. Lab 016 is the first attempt to place
an actual hosted language model behind the same BEAN adapter contract.

Use the model to read a question, decide whether to request a bounded,
read-only fictional probe, and either answer from visible evidence or report
unknown. Fictional supervisor feedback is retained in BEAN SQLite during
training only. A new adapter and database reopening precede holdout testing.
No actual model weights change. Compare to:
- Same hosted LLM without accumulated feedback on the same cases.
- Lab 015 Bayesian emulator on the identical seeded cases.

## Inference setup

GitHub Actions requests a short-lived GITHUB_TOKEN with models:read, which
is documented by GitHub Models. The one-shot workflow runs only when the
specific Lab016 pull request is *opened against main*, in the same repository,
not for every push, other PR, external fork or commit.

Model identifier: openai/gpt-4.1-mini through the
https://models.github.ai/inference/chat/completions endpoint. The GitHub
marketplace currently lists this model; actual API access for this
repository is independently checked by the one-request smoke probe.

Only the public synthetic prompt is sent to the model, never privileged
grading labels, enterprise data or provider context. The token is not
printed or attached to the public report. The host enforces tool allowlist,
max two fictional reference inspections, and DB isolation.

Budget: maximum 72 hosted requests including smoke; at least seven seconds
between starts; output capped to 230 tokens per response; 35-second request
timeout; 15-minute job timeout. There are no unbounded retries. GitHub
Models availability and quotas are subject to the connected account.

## Reproducible paired evaluation

Seed: 7. Training: 12 simulated scenes per arm. Holdout: 12 scenes per arm.
Two arms:
1. hosted model + training feedback + read-only tool
2. same hosted model + read-only tool but no training feedback

The emulator is run on exactly the same synthetic cases for each arm. This
initial small sample is a connectivity/research pilot, not a statistically
powerful assessment of general learning.

Provider errors (including permission denied, quota, malformed response,
and exhausted budget) invalidate the paired hosted comparison. A code test
may pass even if the provider is unavailable, but the experiment report
marks this as UNAVAILABLE or INCOMPLETE, never as an LLM victory.

## Output

The one-shot workflow attaches bean-hosted-llm-lab016.json with synthetic
scores, reported tool calls, separate emulator metrics, model ID,
model availability, request count and sanitized provider errors.

Zero real-world actions, zero verified-world claim promotions, and zero
model weight updates are expected. The experiment is about evidence
evaluation with external hosted neural inference in a simulated world, not
autonomous code rewriting, self-awareness or robot readiness.

## Local offline regression

    python -m pytest bean/tests/test_hosted_models_lab016.py -q

The unit tests use mocked HTTP responses and consume no real inference
tokens. Hosted inference only occurs inside the one-shot workflow or if
an operator intentionally executes:

    GITHUB_TOKEN=... python -m bean.evaluation.hosted_models_lab016 \
        --report bean-hosted-llm-lab016.json --train 12 --holdout 12 \
        --max-calls 72 --interval 7

Keep the report factual: if the API cannot be reached or the model ignores
the response contract, record the failure and repair the experiment without
silently replacing model answers with emulator fixtures.

Lab 016 stacks onto Lab 015 → Lab 014 → Lab 013 → Lab 012 → Lab 011. No merge
to main is implied.

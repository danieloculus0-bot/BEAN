# Lab 026 — Does BEAN's retained evidence actually help?

**Status: controlled experiment on an isolated branch. No model-produced learning advantage has been established.**

## Hypothesis

BEAN's scored and persisted lessons might improve an unchanged coding model's performance on different programming tasks beyond any improvement from ordinary saved context.

This is an ablation of the *evidence-ranked memory component*, not a full general-intelligence evaluation and not training new neural weights.

## Authentic parts reused

The experiment reuses existing Lab 023 real-model learning, BEAN's SHA256-chained SQLite Journal, the loopback-only Ollama adapter, and the independent agent-arena grader. No mocked model reply is counted as a result. Credential-bearing author stages never execute model-written code.

## Four controlled conditions

| Condition | What the same model receives |
| --- | --- |
| Cold | Current task and broken starting source, no saved lessons |
| Simple history | Chronological, unfiltered, model-authored training lessons |
| BEAN evidence | Independently scored BEAN journal lessons, ranked by development score and retaining source-hash references |
| Placebo | Unrelated display/report text, padded to a comparable character budget |

Four rounds rotate all four conditions through different request positions for each task. Both repair tasks are different from the three training exercises. Candidate modules and every prompt are SHA256-receipted before any separate judge executes candidates.

An arm producing no valid candidate receives *no positive credit* and makes the experiment inconclusive rather than proving that BEAN won. The judge rejects mixed providers, mismatched hashes, missing responses, changed journal records and changed public tasks.

## Decision rule and limits

- INCONCLUSIVE: fewer than four repetitions, missing candidates, model mismatch, or incomplete evidence.
- NO_ADVANTAGE_DEMONSTRATED: all candidates compared and no qualifying advantage.
- PRELIMINARY_PILOT_SIGNAL: BEAN's independent-test average exceeds cold, simple history and placebo, without trailing simple history in either task.

Even a preliminary signal cannot establish general learning. The existing public synthetic tasks may be familiar to the model. Strong proof needs novel sealed tasks, more repetitions, matched model/digest and token budgets, cost/time measurements, negative-transfer diagnostics and uncertainty intervals.

## Reproduce with real local Ollama

A working loopback Ollama service with model qwen2.5-coder:1.5b is needed. All artifacts should be in a disposable research directory. Use a credential-free disposable environment for any test execution of generated Python, NOT your usual production BEAN or trading host.

    python -m bean.evaluation.lab023_ollama train --model qwen2.5-coder:1.5b --out lab026
    python -m bean.evaluation.lab023_ollama development --out lab026
    python -m bean.evaluation.causal_ablation_lab026 learn --model qwen2.5-coder:1.5b --root lab026
    python -m bean.evaluation.causal_ablation_lab026 author --model qwen2.5-coder:1.5b --state lab026/state/history.sqlite --out lab026/ablation --trials 4
    python -m bean.evaluation.causal_ablation_lab026 judge --state lab026/state/history.sqlite --artifacts lab026/ablation --out lab026/verdict.json

The final judge runs separately on Windows and Linux, with no access to API keys or local Ollama. The initial experiment uses four rounds (32 candidate calls plus training/reflection). If provider/model calls fail or there are too few verified model-authored lessons, the verdict is inconclusive.

## Ollama support's MiniCheck suggestion

Ollama support suggested the specialized Bespoke MiniCheck factuality checker for evaluating a claim against a given source document. This is relevant as a *different* test: distinguishing supported claims, contradicted claims, and unresolved claims with citation IDs and counterbalanced source ordering. MiniCheck's No means *not supported by this document*, not necessarily refuted by outside reality.

MiniCheck is NOT used to judge whether proposed Python source solves a programming problem; an executable, credential-free withheld-test oracle is needed for that.

## If BEAN does not win

Use the failure data to guide fixes, not lower the acceptance bar:

- Missing model results → improve availability, inference budgets and candidate extraction; report inconclusive.
- Simple history wins → improve task relevance, recency and measured evidence selection.
- Placebo wins → isolate priming, extra context and order sensitivity.
- Cold wins → prevent stale or irrelevant memory from distracting the model.
- Only one domain improves → test genuinely unseen task families before saying memory transfers.

All source hashes, negative results, costs that can be measured and experiment limitations must be retained. No change from this benchmark is allowed to promote model-generated code to production or place actual financial orders.

**First live pilot authorization:** A [lab026-live] commit triggers a real local Ollama experiment in GitHub Actions. Read the generated artifacts and independent verdict, not the green build badge, to determine the result.

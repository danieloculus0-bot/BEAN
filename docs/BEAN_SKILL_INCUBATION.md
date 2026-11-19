# BEAN native skill incubation (BabyAGI 3 inspired)

This is BEAN Core research, not the hosted BEAN note adapter and not BabyAGI's runtime. [BabyAGI 3](https://github.com/yoheinakajima/babyagi3) is a conversational agent that can learn and schedule skills. BEAN reuses its existing Lab019 ModelWriter, run_cycle, disposable trial project, frozen test fingerprints, and SHA-chain SQLite journal. No BabyAGI source is copied.

## Evidence-backed milestone

A model can author a new Python module from a natural-language objective, not just repair an existing file. The native skill incubator stages a missing skill as an intentionally failing placeholder in a disposable copy of a test project, then invokes BEAN's pre-existing Lab019 code search and journal.

1. Independent training tests are frozen before candidate generation. A separate holdout project contains different tests against an identical blank module.
2. A candidate must pass training first. The independent holdout is evaluated only after that gate. Failure ends the run rather than feeding hidden test assertions back to the author.
3. A passing candidate is journaled with source/test/holdout hashes, outcome, and a SHA-chained SQLite event. It is saved under the output validated/bean/skills directory, not installed in Core.
4. A restarted session recovers code from a hash-verified candidate archive. Changed or missing artifacts never silently count as success.
5. Training-only passes retain skill_promotion_ready=false. A separate holdout pass makes a new skill eligible for further review but does not prove generalized intelligence.

## Example with a configured model

Prepare two separate small projects with Python tests directories. Each contains independently authored unittest tests for a not-yet-existing bean.skills.double.double function. Freeze the holdout tests before running.

    python -m bean.optimization.skill_incubator \
      --project experiments/my_skill_training \
      --holdout-project experiments/my_skill_holdout \
      --name double \
      --task "Implement a reusable doubling function for signed integers" \
      --journal local_state/skill_attempts.sqlite \
      --output local_state/skill_artifacts \
      --provider ollama --model qwen2.5-coder:7b --attempts 10

The CLI exits nonzero unless an independent holdout passes. It never writes model code into the original project. A real model must be configured and available. CI exercises synthetic tests and deterministic injected writers, not live model output.

## What remains

- This is skill incubation, not unsupervised daily self-improvement or model-weight learning. BEAN's existing GoalCycle can run registered experiments but is not automatically connected to this module.
- Real learned reuse requires integration with existing BEANReasoningSkills and ExperienceBank, unseen tasks, matched baseline/placebo/memory-ablated comparisons, restart behavior, and independent judgment.
- This change does not establish better drawing or physics reasoning. Those existing experiments need their own receipts.
- The module does not claim to outperform BabyAGI or any other system in general-purpose autonomy.

## BEAN CONTEXT ACK v1

Task: Native BabyAGI-inspired skill creation using existing BEAN infrastructure.
Checked: AGENTS, AI_GATEKEEPER, current main, Lab019, native skills, GoalCycle, Draw, manifest generation 66, Lab019 CI, BabyAGI 3 README.
Reuse: existing model author, disposable evaluator, SHA SQLite journal, output archive.
Ledger: generation 66 manifest candidate 144/144, grammar-matched 144/144. This is not an advantage versus the strong control; no new run claimed.
Unknown: on-device Ollama reachability, model-drawn art quality, real-model skill acquisition and peer head-to-head benchmarks.
Minimum change: staging new modules, independent holdout promotion gate, artifact recovery, CI.
Runtime/policy changes: no changes to normal startup, hosted adapter, robotics, network scheduling or permission policy.

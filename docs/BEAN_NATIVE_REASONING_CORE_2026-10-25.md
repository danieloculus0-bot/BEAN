# BEAN Core: owned native reasoning memory and strategy selection

**Integration scope:** The existing Lab026 reasoning components are promoted into Python BEAN Core. One `NativeReasoningService` opens one SHA-256-chained `ExperienceBank` for source-backed mistakes, proposed procedural skills, model-written rule candidates, measured comparison trials, selected strategies, actual inference and restart recovery. **BEAN owns the state and policy.** Nemotron/OpenAI/Ollama are replaceable inference backends; changing model provider does not erase BEAN's history.

This is a real callable Core integration, **not** proof that the agent has general reasoning intelligence, autonomously sourced true feedback, trained a language model or started trading. The previous research evidence used synthetic problem families. The optional service never runs model calls without an actual configured provider. Candidate hypotheses are marked unverified. Host-reported measurements and source identity remain externally asserted, not independently authenticated.

## Local runtime entry point (Python, no EXE required)

Set `BEAN_REASONING_LESSONS_DB` to a dedicated durable SQLite path; for real model inference also set `BEAN_REASONING_PROVIDER=openrouter` and `OPENROUTER_API_KEY`. The default OpenRouter model is the pinned `nvidia/nemotron-3-ultra-550b-a55b:free`, which may be rate limited. Alternatives: `BEAN_REASONING_PROVIDER=openai` with `OPENAI_API_KEY`, or `ollama` with the configured local server. If the DB is configured without a provider, **memory, retrieval, comparisons and decisions still work**; inference or rule generation returns a clear unavailable error instead of fake success. If the DB is not configured, the existing runtime behavior is unchanged. Run `python bean_run.py --ticks 2` to launch the same local loop with optional reasoning commands installed.

The BEAN command inbox now accepts these commands, all routed to the same `NativeReasoningService`:

| Command | Actual action |
| --- | --- |
| `reasoning_generate` | Ask the actual configured model for a **proposed, unverified** general rule from supplied development examples, and retain its model output with source references |
| `reasoning_reflect` | Persist a source-linked observed mismatch and an unverified correction |
| `reasoning_skill` | Retain an externally reported passed procedure, not execute it |
| `reasoning_instruction` | Store an unverified candidate instruction |
| `reasoning_recall` | Task and domain matched search over durable lessons |
| `reasoning_compare` | Compare fully paired development results across cold, placebo, reflection, skill, and instruction arms; journal the measured strategy choice |
| `reasoning_decide` | Retrieve frozen strategy and matching lessons after restart without calling a provider |
| `reasoning_reason` | Apply the selected BEAN strategy to the task, call one real configured provider, and retain its exact answer and source/hash receipt |
| `reasoning_status` | Report retained lessons, comparisons, strategy choices and inference count without inventing learning outcomes |

Example (Python calling BEAN directly):

```python
from bean.learning import NativeReasoningService

brain = NativeReasoningService("data/bean_reasoning.sqlite3")
try:
    brain.reflect(
        domain="shopfloor", task_id="inspection-42",
        observed="incorrect proposal", expected="verified correction",
        adjustment_hypothesis="check the relevant source evidence first",
        evidence_refs=["verified:external-report-42"])
    # Add multiple procedure and instruction candidates, then use
    # compare/evaluate_and_select on matched development trials.
    # Until there is a measured policy choice, decide() declines to pretend.
    print(brain.status())
finally:
    brain.close()
```

Full actual model trials can also call `evaluate_and_select` / `evaluate_holdout` with a real provider and independent grader, optionally `batched=True` to send multiple questions within an arm. **Do not batch across different arms**, to prevent a memory treatment from being leaked to a cold control.

## What remains unintegrated or unproven

- A human or external verifier still needs to provide trusted, *matched* outcome measurements. BEAN doesn't magically discover authoritative truth from its own generated response.
- The separately integrated SpongeTD Q-values and domain DQN weight checkpoints are **not** the same mechanism as contextual reasoning selection; no blanket claim of general weight training is justified.
- The hosted BEAN connector, BEAN Bridge and AIscend do not automatically invoke this local Core service. Those require explicit authorized adapters and tested real feedback flows, not merely links or merge commits.
- The last Nemotron batched recovery was blocked by HTTP 429 before a complete new held-out result. This merge does not change that historical outcome.
- No automatic trading actions, hardware motion or unattended self-rewriting is added. Reasoning output remains an evidence-bearing proposal/inference.

Acceptance: `python -m unittest bean.tests.test_core_reasoning_integration bean.tests.test_native_reasoning_skills bean.tests.test_batched_trials -v`, full Windows and Ubuntu BEAN Core tests, startup/boot smoke, then merge into `main` with the precise passing head.

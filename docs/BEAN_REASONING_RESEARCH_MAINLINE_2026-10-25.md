# BEAN's reasoning development is in Core — experiments belong in the same repository

**Source status:** research modules integrated alongside the real BEAN Core runtime, with no permission for live trading or autonomous host actions. This document is a publication and provenance index, **not** a declaration that the user's own desktop has been tested.

## One architecture, not another abandoned branch

`bean_run.py` on Core `main` now starts `NativeReasoningService` by default. BEAN owns its SHA-256 chained SQLite ExperienceBank, source-linked reflections, model-authored candidates, strategy comparisons, selected strategy and future reasoning decisions. The external reasoning model (Nemotron free, OpenAI, Ollama) is swappable; neither Q-learning nor a provider alone is the complete BEAN learner.

The local reasoning and learning API is in `bean/learning/reasoning_service.py`, with `bean/learning/native_skills.py` and `batched_trials.py`. These were **actually integrated into main** in [PR #170](https://github.com/danieloculus0-bot/BEAN/pull/170), not merely catalogued.

## Previously stranded experiment code now available in mainline Python

- `python -m bean.evaluation.live_reasoning_transfer`: bounded 18-call same-model real-provider comparison, cold versus irrelevant-memory placebo versus BEAN after persisted restart; no fake success without credentials.
- `python -m bean.evaluation.openrouter_reasoning_transfer`: pinned free Nemotron reasoning adapter. This is a standalone research adapter; `bean.reasoning.openrouter_provider.OpenRouterProvider` is the provider for ordinary BEAN Core.
- `python -m bean.evaluation.nemotron_self_derived_transfer`: **model-authored** rule inference from examples in *two* separate fictional task families. BEAN stores the error, proposes a lesson, assesses a development validation task, chooses from cold / irrelevant placebo / reflection / reusable skill / raw examples, and faces independent same-family holdout tasks after recovering SQLite. Per-arm batching compresses provider requests. Provider 429 is an explicit failed/incomplete run, **not** evidence that BEAN has failed or succeeded at reasoning.
- Offline regression contracts: `python -m unittest bean.tests.test_live_reasoning_transfer bean.tests.test_openrouter_reasoning_transfer bean.tests.test_nemotron_self_derived_transfer`. Their deterministic fixture has no independent learning credit and does not replace the user's desktop test.

## Evidence archive, with original failures

[Full real-model run 40206850819](https://github.com/danieloculus0-bot/BEAN/actions/runs/40206850819) successfully obtained **18 real Nemotron 3 Ultra responses** on a *human-supplied* procedural rule. Two new rule instances scored **2/2 with BEAN's retained reflection**, versus **0/2 cold and 0/2 unrelated placebo**. The actual report, SQLite ledger and hash manifest are preserved under [research/real_reasoning/run-40206850819 on the original experimental branch](https://github.com/danieloculus0-bot/BEAN/tree/experiment/bean-task-matched-transfer-20261025/research/real_reasoning/run-40206850819). The source link is kept because binary source history must not be reconstructed.

[Model-authored follow-on runs 40212952629 and 40212932438](https://github.com/danieloculus0-bot/BEAN/pull/168) derived useful candidate rules but ended in HTTP **429** after 13 and 15 requests respectively. In run 40212952629, the development selection scores were **cold 0/2, irrelevant placebo 0/2, reflection 0/2, skill 1/2, raw examples 2/2**; no completed held-out improvement claim is allowed from that partial run. Its artifacts are intentionally preserved. [PR #169](https://github.com/danieloculus0-bot/BEAN/pull/169) investigated per-arm batching, and its failed recoveries revealed a checksum-transcription error and then provider rate limits. Those failures stay visible rather than being removed from the record.

## Integration vs proof

**Merged source code** means the user can develop it and test it from the Python checkout. **Actual desktop execution** remains unconfirmed in this interaction. **Positive independent learning evidence** is a distinct bar not met simply by merging. We will fix shortcomings on main behind the same provider/configuration and source-controlled boundaries instead of leaving promising mechanisms stale indefinitely.

**Not yet automatic:** hosted BEAN notes, BEAN Bridge, AIscend, Axiom and the existing tabular / neural reward learners do not automatically share all BEAN reasoning outcomes. External real-world feedback still needs reliable host-supplied validation. No model is called without explicit provider configuration; no live trading changed.

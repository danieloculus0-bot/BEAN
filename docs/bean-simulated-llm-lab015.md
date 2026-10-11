# BEAN Lab 015 — Simulation-only reasoning-provider tests

**Scope boundary:** no Jetson, no motor/sensors, no robot deployment,
no live business data, no paid model API, no remote model service.
Everything runs on a disposable software-only simulation database.

## Why this experiment exists

Lab 014 demonstrated source-reliability learning and investigation through
an explicitly scripted fixture. Lab 015 adds a second **emulated reasoning
provider** that consumes the same JSON prompt contract used by a real LLM.

It makes bounded decisions using an explicit Bayesian source-reliability
model. It does **not** generate language by neural inference or train neural
weights, so its performance **must not be described as actual LLM learning**.
It lets us test whether the surrounding BEAN memory, tool, evidence,
uncertainty and recovery interfaces support a future LLM cleanly.

## Simulation phases

Each of three seeds (7, 19, 43) runs three paired variants on the
same synthetic episodes:
1. **Trained + simulated read-only tools:** receives supervisor feedback
   after training decisions, can request reference records in holdouts.
2. **Untrained + tools:** no accumulated feedback, can request records.
3. **Trained + no tools:** gets feedback but cannot investigate.

Training and holdout domains differ. The provider's prompt contains
only visible observations, bounded tools, and past supervised
source-reliability summaries; hidden truth remains in the evaluator.
The emulator deliberately ignores its privileged provider context.
Feedback writes occur ONLY after training decisions and never during
holdout evaluation.

The emulator is re-instantiated after the sandbox SQLite store is closed
and reopened. It has to reconstruct its choices from persisted feedback
and current observations, not retained in-process state.

## Failure-mode coverage

- Correctly treat missing as unknown rather than numeric zero/success
- Distinguish certified fictional evidence from dashboards or stale archives
- Disagreeing certified records produce unknown rather than a fabricated fact
- Refuse to execute arbitrary strings embedded inside simulated documents
- Restrict tool choice to the host's read-only allowlist
- Reject bad or injected provider responses
- Reuse the existing BEAN EpistemicGuard, MemoryStore and TaskEngine
- Check retention after restart and no holdout feedback leakage
- Preserve unverified inference boundaries and zero external actions
- Compare all three arms with the same generated case set

## Run

    python -m pytest bean/tests/test_simulated_llm_lab015.py -q
    python -m bean.evaluation.simulated_llm_lab015 --report sim-lab015.json

For comparison through the Lab 014 interface:

    python -m bean.evaluation.investigation_lab014 --provider simulated --train 30 --holdout 30

**This is not an Ollama runtime.** The emulated provider needs no installed
model, API key, local LLM server or GPU. Its rules are code, inspectable and
deterministic; do not generalize this score to real model intelligence.

## Later milestones (still inside simulations)

- Plug an actual LLM service into the existing provider contract when one
  becomes available on a non-hardware test machine or hosted sandbox.
- Use privately generated and truly unseen cases to reduce overfitting.
- Compare the same model with/without memory and read-only tools.
- Probe longer horizons, novel source types, uncertainty calibration,
  correction and contradiction handling under changing conditions.
- Keep offline scripted/emulated and real-model results in separate tables.

Lab 015 is a draft stacked on Lab 014 → Lab 013 → Lab 012 → Lab 011.
No changes to main are authorized by this lab.

# Brain 0.11 - LLM Reasoning Layer

Brain 0.11 adds a structured reasoning layer to BEAN.

The layer does not make the LLM BEAN's identity. The LLM is a reasoning and language provider. BEAN's identity remains in local memory, continuity, event records, body-state history, reflections, and developmental records.

## What it does

- Builds a compact reasoning context from BEAN state.
- Calls a provider such as the deterministic stub or a live provider.
- Validates proposed action candidates.
- Persists `ReasoningProposal` records.
- Persists action candidates as `proposed` records only.
- Allows proposals to reference speculative hypothesis IDs.

## What it does not do

- It does not execute action candidates.
- It does not enable motion.
- It does not touch hardware drivers.
- It does not claim sentience or emotion.

## Safety invariants

- `motion_enabled` remains false.
- Motion candidates cannot be validated for execution inside reasoning.
- Accepted candidates remain database decisions, not physical actions.
- The supervisor gate remains separate from any future actuator layer.

## Main files

- `bean/reasoning/provider_base.py`
- `bean/reasoning/proposal.py`
- `bean/reasoning/context_builder.py`
- `bean/reasoning/action_validator.py`
- `bean/reasoning/reasoning_engine.py`
- `bean/reasoning/providers/stub_provider.py`
- `bean/tests/test_reasoning_module.py`

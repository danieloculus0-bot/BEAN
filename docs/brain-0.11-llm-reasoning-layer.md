# Brain 0.11 - OpenAI-Preferred Reasoning Layer

Purpose: let BEAN assemble bounded context and ask a reasoning provider for structured proposals.

The LLM is a tool. It is not BEAN identity.

## What it does

- Builds a bounded context packet.
- Builds a JSON-only prompt contract.
- Uses a mock provider for tests.
- Provides an OpenAI provider placeholder for real use.
- Parses model output into structured proposal fields.
- Filters proposals for epistemic, dignity, motion, and memory risks.
- Stores proposals for supervisor review.

## What it is not

- Not an action executor.
- Not a direct memory writer.
- Not a motion controller.
- Not BEAN identity.

## Main modules

```text
bean/reasoning/context_builder.py
bean/reasoning/prompt_builder.py
bean/reasoning/mock_llm.py
bean/reasoning/openai_provider.py
bean/reasoning/response_parser.py
bean/reasoning/proposal_filter.py
bean/reasoning/proposal_store.py
bean/reasoning/reasoning_engine.py
```

## Test

```bash
python3 bean/tests/test_reasoning_layer.py
```

## Provider note

OpenAI is the preferred real provider. Tests remain offline and use the mock provider.

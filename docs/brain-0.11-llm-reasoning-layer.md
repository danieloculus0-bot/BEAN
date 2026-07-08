# Brain 0.11 - OpenAI-Preferred Reasoning Layer

Purpose: let BEAN assemble bounded context and ask a reasoning provider for structured proposals.

The LLM is a tool. It is not BEAN identity, memory, or an action path.

## What it does

- Builds a bounded context packet from BEAN records.
- Builds a JSON-only prompt contract.
- Uses a mock provider for tests.
- Provides an OpenAI provider for configured real use.
- Parses model output into structured proposal fields.
- Filters proposals for epistemic, dignity, body-output, and memory risks.
- Stores proposals for supervisor review.

## Reasoning context packet

The context packet now includes bounded slices of:

```text
identity
origin_covenant
active_boundaries
capabilities
recent_events
active_world_claims
uncertainty_claims
wisdom_recent_traces
relationship_summaries
speculative_summary
body_output_status
```

The packet also stores the row IDs it used:

```text
included_event_ids_json
included_claim_ids_json
included_wisdom_trace_ids_json
included_relationship_ids_json
```

This makes reasoning proposals traceable back to the records they were allowed to see.

## What it is not

- Not an action executor.
- Not a direct memory writer.
- Not a body controller.
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

## Tests

```bash
python3 bean/tests/test_reasoning_layer.py
python3 bean/tests/test_reasoning_context_packet.py
```

## Provider note

OpenAI is the preferred configured provider. Tests remain offline and use the mock provider.

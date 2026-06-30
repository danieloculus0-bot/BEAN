# Brain 0.12 - OpenAI Responses API Provider

Brain 0.12 adds an optional OpenAI reasoning provider.

The provider is optional. If `OPENAI_API_KEY` is not present, BEAN falls back to the deterministic `StubProvider`.

## API behavior

- Uses `requests`, not the OpenAI SDK.
- Uses the OpenAI Responses API endpoint `/v1/responses`.
- Requests strict JSON Schema structured output.
- Treats refusal and incomplete responses as errors.
- Revalidates returned JSON locally.

## Safety behavior

- Provider output becomes `ReasoningOutput` only.
- Reasoning output becomes `ReasoningProposal` records only.
- Candidate records remain proposed.
- No physical motion is executed.
- No hardware libraries are imported by the provider.
- Forbidden fake emotion, fake sentience, and unsupported identity language are rejected or redacted.

## Live use

Set environment variables outside the repo:

```bash
export OPENAI_API_KEY="sk-..."
export BEAN_LLM_MODEL="gpt-4o-mini"
```

Do not commit secrets.

## Main files

- `bean/reasoning/providers/openai_provider.py`
- `bean/tests/test_openai_provider.py`

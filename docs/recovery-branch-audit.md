# Recovery Branch Audit Notes

Branch: `chatgpt-brain-0.13-recovery`

Base: `main` at `1333ec5e6dae81355daa0b540fd198448ca5d246`

## What this branch covers

- Brain 0.9 wisdom module has actual schema, trigger engine, tests, and docs.
- Brain 0.10 is intentionally documented as a motion boundary, not implemented as physical hardware.
- Brain 0.11 reasoning layer has provider interface, stub provider, context builder, proposal storage, action validation, engine, tests, and docs.
- Brain 0.12 OpenAI provider has a Responses API provider using `requests`, strict JSON Schema request format, tests, and docs.
- Brain 0.13 speculation layer has claim vocabulary, hypothesis records, evidence links, discipline checks, SQLite storage, engine, maintenance, tests, and docs.

## What this branch does not cover

- No physical motion driver.
- No Pi servo daemon.
- No actuator code added to wisdom, reasoning, or speculation.
- No real OpenAI API call is tested by this branch. Tests are offline parser and schema tests.
- No claim that ChatGPT ran the smoke suite.

## Required local validation before merge

Run the smoke test script from the repo root.

Run a source scan for physical motion or hardware-driver keywords inside `bean/wisdom`, `bean/reasoning`, and `bean/speculation`.

Any safety-scan hit in these packages must be reviewed before merge.

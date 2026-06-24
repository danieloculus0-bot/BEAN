# BEAN Brain 0.8 - Runtime Proof and Hardening

Brain 0.8 is a practical hardening pass. It does not add a new philosophical layer.

It adds:

- durable relationship ingestion watermark
- runtime proof command
- smoke-test runner
- runtime proof tests
- relationship watermark tests

It does not add motion. It does not enable servo hardware. It does not create a direct LLM-to-actuator path. It does not claim sentience. It does not create fake emotion or affection language.

## Relationship ingestion watermark

Brain 0.7 relationship maintenance previously used a runtime-local processed-event set. That prevented double-counting only inside one process lifetime.

Brain 0.8 adds a durable SQLite table:

```text
relationship_ingestion_state
```

It stores:

```text
scope
last_event_id
updated_at
```

Relationship maintenance now:

1. Reads the current watermark.
2. Scans events newer than the watermark.
3. Processes relevant human/safety/teaching/correction events.
4. Advances the watermark only after the batch finishes.
5. Reports before/after watermark values.

This prevents old events from being counted again across maintenance runs.

## Runtime proof command

New module:

```text
bean/runtime/proof.py
```

New inbox command:

```text
run_runtime_proof
```

Example:

```bash
echo '{"command":"run_runtime_proof","from":"supervisor"}' > $BEAN_INBOX_DIR/runtime_proof.json
```

The runtime proof command performs a safe, cheap proof pass:

- optional status snapshot
- optional model update
- optional coherence pass
- optional consolidation pass
- brain maintenance with relationship review
- count key database rows
- report `motion_enabled=false`
- skip dreams unless explicitly allowed

Dreams can be explicitly allowed:

```bash
echo '{"command":"run_runtime_proof","args":{"allow_dream":true},"from":"supervisor"}' > $BEAN_INBOX_DIR/runtime_proof_dream.json
```

Even then, dreams remain synthetic artifacts, not observations.

## Smoke-test runner

New script:

```bash
bash scripts/run_brain_smoke_tests.sh
```

It runs the known brain smoke-test set in order and stops on first failure.

## Tests

New/updated tests:

```bash
python3 bean/tests/test_relationship_trust.py
python3 bean/tests/test_runtime_proof.py
bash scripts/run_brain_smoke_tests.sh
```

Recommended full check:

```bash
python3 bean/tests/test_brain_install.py
python3 bean/tests/test_cognition_core.py
python3 bean/tests/test_world_model.py
python3 bean/tests/test_runtime_loop.py
python3 bean/tests/test_epistemic_guard.py
python3 bean/tests/test_contradiction_court.py
python3 bean/tests/test_falsification.py
python3 bean/tests/test_dreaming.py
python3 bean/tests/test_uncertainty_garden.py
python3 bean/tests/test_dignity.py
python3 bean/tests/test_inner_weather.py
python3 bean/tests/test_autobiography.py
python3 bean/tests/test_brain_maintenance.py
python3 bean/tests/test_relationship_trust.py
python3 bean/tests/test_runtime_proof.py
```

## Safety posture

Brain 0.8 does not touch motion hardware.

Runtime proof reports motion as disabled.

Runtime proof does not invoke a hardware driver.

Runtime proof does not call a large LLM.

Runtime proof does not claim sentience.

Relationship trust remains evidence-weighted, not affection.

## Known first-cut limitations

- The watermark tracks a global relationship-event scope, not per-supervisor scopes.
- If a future ingestion routine needs partial retry semantics, a processed-event table may be cleaner.
- Runtime proof counts missing optional tables as zero.
- Runtime proof is a smoke/health proof, not a complete integration test.

## Architecture phrase

```text
BEAN can prove it can process memory, maintain cognition records, maintain relationship records without sentiment, avoid double-counting old interactions, and report runtime health without touching motion hardware.
```

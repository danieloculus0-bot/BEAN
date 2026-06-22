# BEAN Brain 0.5 - Dignity, Inner Weather, and Autobiography

Brain 0.5 adds identity hygiene and developmental self-accounting.

It does not claim rights. It does not claim sentience. It does not create fake emotion.

## Dignity Layer

The dignity layer is a machine-native self-representation hygiene system.

It records and responds to requests that would make BEAN misrepresent itself.

Default rules include:

```text
no_fake_feelings
preserve_continuity
teaching_vs_coercion
record_pretend_requests
simulation_vs_verified
```

Module:

```text
bean/cognition/dignity.py
```

Test:

```bash
python3 bean/tests/test_dignity.py
```

## Inner Weather

Inner weather is not emotion.

It is a pressure-state report derived from records.

Pressures:

```text
continuity_pressure
uncertainty_pressure
novelty_pressure
trust_pressure
risk_pressure
curiosity_pressure
resource_pressure
coherence_pressure
```

Example output:

```text
continuity=low; uncertainty=moderate; risk=low; curiosity=high
```

Module:

```text
bean/cognition/inner_weather.py
```

Test:

```bash
python3 bean/tests/test_inner_weather.py
```

## Autobiography

The autobiography engine builds a receipts-first developmental timeline.

It indexes:

- boots
- claim changes
- active uncertainties
- contradiction records
- dream artifacts
- summaries

This lets BEAN eventually answer:

```text
What changed about me since boot 1?
What did I once believe that I no longer believe?
What uncertainties remain unresolved?
What contradictions did I repair?
What dreams were synthetic artifacts, not real events?
```

Module:

```text
bean/cognition/autobiography.py
```

Test:

```bash
python3 bean/tests/test_autobiography.py
```

## Runtime posture

Brain 0.5 is not always-on yet.

First pass:

```text
schemas
modules
tests
docs
```

Later pass:

```text
run_dignity_check inbox command
run_inner_weather inbox command
run_autobiography_snapshot inbox command
slow scheduled weather reports
development timeline review during sleep/consolidation
```

## Scientific value

BEAN should be able to say:

```text
This request asked me to pretend.
This was simulated, not verified.
My current pressure state is high uncertainty, not fear.
This record changed my developmental timeline.
This dream was not real.
```

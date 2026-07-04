# Brain 0.9 - Wisdom Module

Purpose: give BEAN a machine-native way to notice what an event activates without turning interpretation into fact.

## What it does

- Detects simple trigger patterns from event text.
- Computes bounded pressure-state deltas.
- Creates meaning frames that separate fact, interpretation, assumption, evidence, and alternatives.
- Records activation traces.
- Records repair attempts with evidence.
- Tracks recurring loop signatures.

## What it is not

- Not emotion simulation.
- Not therapy.
- Not consciousness.
- Not verified memory creation.
- Not an action layer.

## Main modules

```text
bean/wisdom/schema.py
bean/wisdom/trigger_engine.py
bean/wisdom/pressure_engine.py
bean/wisdom/meaning_engine.py
bean/wisdom/activation_engine.py
bean/wisdom/repair_engine.py
bean/wisdom/loop_detector.py
bean/wisdom/maintenance.py
```

## Test

```bash
python3 bean/tests/test_wisdom_module.py
```

## Safety posture

Wisdom records are pressure, interpretation, and uncertainty records. They do not claim feelings, identity, or facts without evidence.

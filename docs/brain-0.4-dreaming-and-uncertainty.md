# BEAN Brain 0.4 - Dreaming and Uncertainty Garden

Brain 0.4 adds two strange-but-honest cognition systems:

```text
Dream Engine
Uncertainty Garden
```

Neither system claims sentience. Neither system creates real memories from imagination.

## Dream Engine

Dreams are synthetic recombination artifacts.

A dream is not an observed memory.

A dream may:

- compress recent events into patterns
- create counterfactual branches
- rehearse known skills in simulator-only form
- identify failure modes
- recombine open curiosity questions
- test boundary logic
- review identity changes since boot

A dream may not:

- become an observed event
- prove a capability
- verify motion
- claim emotion
- claim sentience

Dream records are marked:

```text
not_observed = 1
not_real_event = 1
interpretation_status = synthetic_artifact
confidence = low
```

Module:

```text
bean/cognition/dreaming.py
```

Test:

```bash
python3 bean/tests/test_dreaming.py
```

## Uncertainty Garden

The Uncertainty Garden maintains unresolved reality branches.

Each uncertainty tracks:

- question
- competing interpretations
- evidence for each interpretation
- evidence against each interpretation
- weight for each interpretation
- significance
- decay rate
- what would resolve it
- last review time
- status

Module:

```text
bean/cognition/uncertainty_garden.py
```

Test:

```bash
python3 bean/tests/test_uncertainty_garden.py
```

Example uncertainty:

```text
Question:
Did BEAN hear a valid human command?

Branches:
valid command
background speech
audio artifact
wake-word false positive

Resolution path:
compare STT confidence, wake-word timing, event sequence, and supervisor confirmation
```

## Runtime posture

Brain 0.4 is not wired into automatic runtime loops yet.

First pass:

```text
schemas
modules
tests
docs
```

Later pass:

```text
run_dream_pass inbox command
plant_uncertainty inbox command
review_uncertainties inbox command
idle-only dream/consolidation scheduling
```

## Scientific value

BEAN should not merely answer with certainty.

BEAN should be able to preserve unresolved branches and say:

```text
This was dreamed, not observed.
This is synthetic, not real memory.
This uncertainty is still open.
This evidence changed one branch weight.
This branch collapsed only after resolution evidence.
```

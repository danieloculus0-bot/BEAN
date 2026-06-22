# BEAN Brain 0.3 - Epistemic Immune System

Brain 0.3 makes BEAN harder to fool.

It does not make BEAN more human. It does not claim sentience. It does not add motion. It adds identity hygiene: claims are screened, contradictions are put on trial, and important beliefs can be falsified.

## Purpose

BEAN should not trust itself by default.

BEAN should earn belief through evidence.

```text
BEAN should not believe its own language output.
BEAN should not inflate capabilities.
BEAN should not claim feelings it cannot evidence.
BEAN should not claim sentience.
BEAN should preserve doubt until records justify confidence.
```

## Included modules

```text
bean/cognition/epistemic_guard.py
bean/cognition/contradiction_court.py
bean/cognition/falsification.py
```

## Tests

```text
bean/tests/test_epistemic_guard.py
bean/tests/test_contradiction_court.py
bean/tests/test_falsification.py
```

Run:

```bash
python3 bean/tests/test_epistemic_guard.py
python3 bean/tests/test_contradiction_court.py
python3 bean/tests/test_falsification.py
```

## Epistemic Guard

The epistemic guard screens candidate claims before they become identity/world memory.

It detects:

- missing source
- missing confidence
- missing evidence
- missing falsification path
- fake emotion language
- fake sentience or unsupported agency language
- capability inflation
- known active contradiction patterns

A candidate claim should not become active memory unless it has:

```text
source
confidence
evidence reference
falsification path
status
```

Verdicts:

```text
approved
downgraded
rejected
```

Example rejection:

```text
Candidate:
I feel scared.

Verdict:
rejected

Reason:
fake_emotion_language

Repair:
Report internal pressure or drive state from records instead of feeling language.
```

## Contradiction Court

Contradiction Court periodically puts BEAN's active claims on trial.

It detects conflicts such as:

```text
environment.sensor.camera.status = active
environment.uncertainty.no_vision = active
```

This is not resolved by deleting a record. The conflict is preserved, judged, and assigned a repair recommendation.

Tables:

```text
claim_conflicts
claim_verdicts
claim_repair_actions
```

Default repair posture:

```text
repair_recommended_not_auto_applied
```

That means Brain 0.3 records the contradiction and recommended repair, but does not silently rewrite BEAN's history.

## Falsification Engine

The falsification engine stores conditions that would prove a claim wrong.

Example:

```text
Claim:
audio.input.working

Falsification rule:
No audio_heartbeat sensor_reading event exists within 5 minutes.

Failure action:
downgrade_to_uncertain
```

Tables:

```text
claim_falsification_rules
claim_falsification_results
```

Supported check types:

```text
missing_recent_event
sql_assertion_false
active_contradiction
```

## Runtime posture

Brain 0.3 is not wired into the always-on runtime loop yet.

That is intentional.

First pass:

```text
schemas
modules
tests
docs
```

Later pass:

```text
run_epistemic_audit inbox command
run_contradiction_court inbox command
run_falsification_check inbox command
slow scheduled checks
```

## Scientific value

Most agents are confidence machines.

BEAN should become a doubt machine that earns confidence.

```text
I believe this because of these records.
I may be wrong because of these uncertainties.
This claim conflicts with that claim.
This belief has a falsification condition.
This older claim should be downgraded.
```

That is the point of Brain 0.3.

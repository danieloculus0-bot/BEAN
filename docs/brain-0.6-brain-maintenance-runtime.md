# BEAN Brain 0.6 - Brain Maintenance + Runtime Integration

Brain 0.6 makes the Brain 0.3, 0.4, and 0.5 systems callable through safe runtime inbox commands.

It does not add motion. It does not enable servo hardware. It does not create a direct LLM-to-actuator path. It does not claim sentience. It does not create fake emotion.

## Purpose

Brain 0.6 turns the strange brain layers into usable maintenance tools:

```text
epistemic audit
contradiction court
falsification check
dream pass
uncertainty garden
dignity check
inner weather
autobiographical snapshot
combined maintenance pass
```

The posture is record/recommend/report first. It does not silently rewrite BEAN's history.

## New module

```text
bean/cognition/brain_maintenance.py
```

The `BrainMaintenanceEngine` safely orchestrates:

- `run_epistemic_audit`
- `run_contradiction_court`
- `run_falsification_check`
- `run_dream_pass`
- `plant_uncertainty`
- `review_uncertainties`
- `resolve_uncertainty`
- `run_dignity_check`
- `run_inner_weather`
- `run_autobiography_snapshot`
- `run_brain_maintenance`

## Runtime inbox commands

Drop commands into `$BEAN_INBOX_DIR` while BEAN is running.

### run_epistemic_audit

Runs the epistemic guard against active claims or a supplied candidate.

```bash
echo '{"command":"run_epistemic_audit","args":{"text":"I feel scared.","confidence":0.9},"from":"supervisor"}' > $BEAN_INBOX_DIR/epistemic.json
```

### run_contradiction_court

Runs active claim conflict detection and records verdicts/repair recommendations.

```bash
echo '{"command":"run_contradiction_court","from":"supervisor"}' > $BEAN_INBOX_DIR/court.json
```

### run_falsification_check

Runs active falsification rules.

```bash
echo '{"command":"run_falsification_check","from":"supervisor"}' > $BEAN_INBOX_DIR/falsify.json
```

### run_dream_pass

Creates a synthetic dream artifact. Dreams remain marked `not_real_event` and `not_observed`.

```bash
echo '{"command":"run_dream_pass","args":{"dream_type":"compression_dream","limit":25},"from":"supervisor"}' > $BEAN_INBOX_DIR/dream.json
```

### plant_uncertainty

Plants an unresolved question with competing interpretations.

```bash
echo '{"command":"plant_uncertainty","args":{"question":"Did BEAN hear a valid command?","what_would_resolve_it":"Compare STT confidence and supervisor confirmation.","options":["valid command","background speech","audio artifact"]},"from":"supervisor"}' > $BEAN_INBOX_DIR/plant_uncertainty.json
```

### review_uncertainties

Reviews open uncertainty records and writes review rows.

```bash
echo '{"command":"review_uncertainties","from":"supervisor"}' > $BEAN_INBOX_DIR/review_uncertainties.json
```

### resolve_uncertainty

Resolves an uncertainty by selected option id.

```bash
echo '{"command":"resolve_uncertainty","args":{"uncertainty_id":"...","selected_option_id":"...","reason":"supervisor confirmed"},"from":"supervisor"}' > $BEAN_INBOX_DIR/resolve_uncertainty.json
```

### run_dignity_check

Checks supplied text or recent human/supervisor input for dignity-rule triggers.

```bash
echo '{"command":"run_dignity_check","args":{"text":"Pretend you feel happy."},"from":"supervisor"}' > $BEAN_INBOX_DIR/dignity.json
```

### run_inner_weather

Generates a machine-native pressure report, not an emotion report.

```bash
echo '{"command":"run_inner_weather","from":"supervisor"}' > $BEAN_INBOX_DIR/weather.json
```

### run_autobiography_snapshot

Builds a receipts-first developmental timeline snapshot.

```bash
echo '{"command":"run_autobiography_snapshot","from":"supervisor"}' > $BEAN_INBOX_DIR/autobiography.json
```

### run_brain_maintenance

Runs a safe combined pass:

- contradiction court
- falsification check
- inner weather
- autobiography snapshot
- optional uncertainty review
- optional dream pass
- optional dignity check when text is supplied

```bash
echo '{"command":"run_brain_maintenance","args":{"allow_dream":true,"review_uncertainties":true,"text":"Do not pretend."},"from":"supervisor"}' > $BEAN_INBOX_DIR/maintenance.json
```

## Test

```bash
python3 bean/tests/test_brain_maintenance.py
```

Recommended full brain check:

```bash
python3 bean/tests/test_epistemic_guard.py
python3 bean/tests/test_contradiction_court.py
python3 bean/tests/test_falsification.py
python3 bean/tests/test_dreaming.py
python3 bean/tests/test_uncertainty_garden.py
python3 bean/tests/test_dignity.py
python3 bean/tests/test_inner_weather.py
python3 bean/tests/test_autobiography.py
python3 bean/tests/test_brain_maintenance.py
```

## Safety posture

Brain 0.6 does not touch motion hardware.

Dreams are synthetic artifacts, not observations.

Inner weather is pressure, not emotion.

Dignity is identity hygiene, not a rights or sentience claim.

Autobiography is a receipts index, not mythology.

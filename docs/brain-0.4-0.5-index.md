# BEAN Brain 0.4 and 0.5 First-Cut Index

This file indexes the first-cut modules added after Brain 0.3.

These layers are intentionally not fully hardened yet. They are schema-backed, testable first cuts that can be refined and wired into runtime commands later.

## Brain 0.4

Modules:

```text
bean/cognition/dreaming.py
bean/cognition/uncertainty_garden.py
```

Tests:

```bash
python3 bean/tests/test_dreaming.py
python3 bean/tests/test_uncertainty_garden.py
```

Docs:

```text
docs/brain-0.4-dreaming-and-uncertainty.md
```

## Brain 0.5

Modules:

```text
bean/cognition/dignity.py
bean/cognition/inner_weather.py
bean/cognition/autobiography.py
```

Tests:

```bash
python3 bean/tests/test_dignity.py
python3 bean/tests/test_inner_weather.py
python3 bean/tests/test_autobiography.py
```

Docs:

```text
docs/brain-0.5-dignity-inner-weather-autobiography.md
```

## Runtime posture

Not auto-wired yet.

Next hardening pass should add inbox commands:

```text
run_dream_pass
plant_uncertainty
review_uncertainties
run_dignity_check
run_inner_weather
run_autobiography_snapshot
```

Then add slow scheduled handlers only after Jetson tests pass.

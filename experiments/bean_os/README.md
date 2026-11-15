# BEAN OS Virtual Desktop Experiment v2

This experiment connects **real BEAN Python Core** native reasoning to an isolated,
resettable *simulated* PC. It is not a live desktop controller. No user data,
third-party LLM, command shell, or host system resource is exposed.

## Environment

Five subsystems: **storage**, **services**, **network**, **files**, and **apps**.
Each has two repair tools and a no-op inspection choice. A virtual desktop
represents files, a document/backup, a browser, a desktop service, DNS/routing,
and storage permissions. Its host simulates what each action changes.

The host exposes numeric observations and measured intervention rewards, **not
the correct tool or the hidden condition**. The existing
`NativeReasoningService.discover_analogy` fits a bounded rule using 60 observed
training states, 12 measured **passively sampled** probes and 12 validation states *per subsystem*. The active disagreement sampler was separately found to overselect healthy observations in this environment; that limitation is retained as an open BEAN learning defect.
The selected policy and its evidence are retained by BEAN's existing SQLite
SHA journal. All policies are reloaded from storage before any blind episode.

36 held-out multi-fault workstations then exercise the observe, decide, act,
reinspect, and verify loop. Each episode is logged in the same BEAN journal,
including failures and wasted repair attempts. Tool actions are limited to
the simulated world; the real host is never touched.

## Measurement

- Blind whole-desktop restoration rate, target >=80%.
- Repair fraction across initial simulated faults.
- Unnecessary repair action rate, target <=10%.
- Persisted episode receipts, target all 36.
- Exact decisions, observed signals, tool calls, and post-action observations.

A no-op baseline makes no repairs on any faulty episode. This benchmark measures
only the limited registered problem families, not open-ended troubleshooting,
general intelligence, generalization to novel repair operations, or actual OS
control. These cases are created and scored by the *same repository* and are not
an independently authenticated assessment. A failure is reported, never hidden
by modifying the score threshold.

## Run

From BEAN repo root with Python 3.11+:

```bash
python -m unittest discover -s tests -p 'test_bean_os_virtual_desktop.py' -v
python -m experiments.bean_os.virtual_desktop --output artifacts/bean-virtual-desktop.json
```

CI: `.github/workflows/bean-os-virtual-desktop.yml`

## Next

Add durable task queues with generated goals, unfamiliar symptoms, dependent
operations, incomplete observations, and realistic recovery from interrupted
sessions. Then implement an opt-in adapter for a real user desktop and an
authenticated BEAN ChatGPT plugin bridge. Do not confuse simulated operation
with physical workstation control.

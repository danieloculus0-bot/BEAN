# BEAN Cognitive Gauntlet: delayed-feedback sensor reliability

**Promoted as an isolated, callable research component on main, 2026-10-29.**
This is not activated by the BEAN Core reasoning runtime and does not train
neural weights or execute an external AGI project. The exact original
Gauntlet implementation and tests came from commit
[fe8e45c4](https://github.com/danieloculus0-bot/BEAN/commit/fe8e45c4ae1d84c96bd7006f612ff37c0f4554d7).
The separate draft [PR #199](https://github.com/danieloculus0-bot/BEAN/pull/199)
and its original case-level evidence remain unchanged. The [16-job exact-head
Gauntlet run](https://github.com/danieloculus0-bot/BEAN/actions/runs/40872602958)
passed before this promotion; that does not certify this new main commit.
The mainline independent verification is the
[BEAN sensor feedback regression](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-sensor-feedback.yml).

## Mechanism

`sensor_reliability.py` learns per-origin binary observation reliability
through Beta success/failure counts. When a verified binary outcome is
provided **after** a forecast, the agent updates its learned accuracy for
each sensor that contributed to the forecast. A persistently wrong sensor
may become *negative* evidence and its vote is inverted by the likelihood
ratio. The `forgetful` arm applies 0.97 counter decay per delayed feedback
to recover when previously reliable sources become unreliable.

Every evidence receipt has an ID. The model rejects repeated IDs, duplicate
origins in one forecast, malformed inputs, duplicate feedback, and saving
state while a result is pending. `state()` and `restore()` preserve
counters, evidence IDs and feedback history across restart.

Source identities and verified outcomes are supplied by the simulator. This
is a *conditional* test: without trustworthy outcome feedback, the model
cannot independently know the truth of its sensors' reports.

## Fair controls

Each case uses the same five observations and ground-truth label. All
forecasts are produced **before** the label is delivered.

- `fixed_prior`: unmodified Beta(3,1) prior, reset every round.
- `long_memory`: source-specific online posterior, no decay.
- `forgetful`: same source learning with factor 0.97 decay.
- `unweighted`: ordinary current-tick observation mean.

The reference arms are small experimental baselines, not full BEAN Core
invocations. The environment is entirely synthetic, with no external
OpenNARS/PLN/Hyperon/Voyager/Letta/Dreamer runtimes.

## Local evidence (not CI-certified)

The original local replay is 30 seeds × 120 rounds × 6 environments =
**21,600 case-level prediction comparisons**. MSE (lower is better):

| Scenario | Fixed prior | Long memory | Forgetful | Unweighted |
| --- | ---: | ---: | ---: | ---: |
| Diverse sensor quality | 0.06004 | **0.04856** | 0.04927 | 0.08359 |
| Adversarial sensors | 0.25499 | **0.03675** | 0.03839 | 0.22996 |
| Weak information | 0.34478 | **0.27100** | 0.27511 | 0.28403 |
| Source quality swaps halfway | 0.31455 | 0.32352 | **0.15874** | 0.26021 |
| Rapidly changing truth | 0.19178 | **0.03653** | 0.03776 | 0.18990 |
| Correlated sensor triplets | 0.17748 | **0.14517** | 0.14632 | 0.21770 |
| **All conditions** | 0.22394 | 0.14359 | **0.11760** | 0.21090 |

The forgetting version **regresses** against long memory in five of
six regimes, but recovers much better when sources swap reliability. The
non-forgetting online model even loses to the fixed-prior control in
the source-swap case. These negative outcomes are retained in the archive.

Because parameter choice and experimental structure were informed by
prior synthetic failures, this is **not** an independent externally held
benchmark of generalization. In particular, correlated sensor errors can
make the naive-independence Bayesian forecasts overconfident.

## Reproduction and receipts

```sh
python -m unittest bean.tests.test_cognitive_sensor -v
python -m experiments.cognitive_gauntlet.sensor_benchmark
```

The runner generates
`cognitive-gauntlet-results/sensor-feedback.json.gz`. It contains every
source observation, forecast, per-arm squared loss, learned reliability
snapshot **before feedback**, ground-truth outcome, seed, and summary.
It includes an SHA-256 of canonical unsigned data and checks exact gzip
round-trip integrity. Missing or failed cases must not be dropped.
The GitHub Action tests Linux/Windows and Python 3.11/3.12.

The next experiment should test **missing or delayed feedback**, unreliable
feedback, correlated sources, and source identity spoofing before claiming
broader autonomy. This implementation is available on main for explicit
research imports, not enabled in production cognition or promoted as a
validated real-world intelligence gain.

## Missing-outcome continuation and independent failure-path holdout (2026-10-29)

Mainline research code now offers `skip_feedback(reason=...)` to close a forecast
whose outcome was **not supplied**, without treating the absence as a wrong
or correct sensor prediction. It does not update or decay learned trust,
retains the original consumed evidence IDs, and appends an explicit
`outcome: null` receipt. Checkpoint restoration validates these receipts;
older observed-outcome checkpoints remain readable. Skipping is irreversible
through this single-pending-forecast interface: late-arriving labels require
a separately designed and tested asynchronous learner. The host must explicitly
declare missing feedback; BEAN cannot authenticate the declaration.

The new `sensor_missing_feedback.py` benchmark uses **predeclared new seeds
26000 to 26011**, 100 rounds per seed, and four synthetic regimes (4,800
total forecasts). The existing 0.97-decay learner, prior and parameters
are frozen; no holdout tuning. A matched oracle receives every delayed
label; the partial-feedback learner receives the same observations but skips
missing outcomes; a fixed prior and unweighted vote are additional controls.
The oracle is **not deployable** in a missing-label environment. Both
random missingness and outcome-dependent selective missingness are tested.
Each case retains the original observations, truth held by the evaluator,
predictions, losses, before/after trust counts, and whether feedback arrived.

**Locally executed result** (Python, 2026-10-29; exact GitHub CI is
a separate verification): 5/5 missing-feedback tests passed. 4,800
synthetic forecasts, 1,657 missing labels, full-feedback oracle MSE
0.113102, partial-feedback MSE **0.169053**, fixed-prior 0.190142,
unweighted 0.174042. Lower is better. In the most hostile
`swap_selective` regime, missing feedback **regressed** to 0.368322
versus fixed-prior 0.325195 and unweighted 0.267533. This is a real
limitation: feedback absence correlated with hard cases biases the
available learning signal. In `diverse_random`, partial feedback
0.047236 versus oracle 0.047612 (small stochastic difference, not
evidence of superiority). Full original negative cases are archived
by the new workflow artifact, without modifying prior ledgers.

Reproduce:
```sh
python -m unittest bean.tests.test_cognitive_sensor_missing -v
python -m experiments.cognitive_gauntlet.sensor_missing_feedback
```

This is a safe continuation and evidence-integrity improvement, **not**
a demonstrated cross-domain generalization gain, real-world sensor
authentication, consciousness, AGI or a production Core integration.

## Checkpoint evidence identity hardening (2026-10-29)

The existing learner now rejects checkpoints with malformed, duplicated or
unaccounted evidence IDs: every consumed ID must occur exactly once in an
observed or explicitly missing-feedback receipt. Non-string IDs and origins
are rejected before a forecast can consume them. Returned checkpoint receipts
and restored receipts are deep-copied, so modifying a caller's snapshot cannot
silently rewrite the live model's history. Targeted negative regression tests
cover forged IDs, dropped IDs, duplicate receipts, invalid types and snapshot
aliasing. This does **not** authenticate host-provided outcomes or detect a
malicious caller who directly edits the model's public in-memory attributes.
Prediction mathematics and existing frozen benchmark parameters are unchanged.

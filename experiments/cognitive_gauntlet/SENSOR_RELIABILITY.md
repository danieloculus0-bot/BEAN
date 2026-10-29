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

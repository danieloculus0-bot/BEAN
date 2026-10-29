# Measuring BEAN's judgment: five separate dimensions

**Experimental only**. This is a *post-hoc* evaluation of the existing
Schrödinger's Logic synthetic sensor-decision benchmark, not a general
intelligence test. No BEAN Core runtime changes, external AGI opponents, or
quantum hardware are involved. The experiment measures the user's proposal
that a wrong decision may still follow reasonable deliberation.

Use:

```sh
python -m unittest bean.tests.test_cognitive_wisdom -v
python -m experiments.cognitive_gauntlet.wisdom_benchmark
```

The runner writes `cognitive-gauntlet-results/wisdom-measurement.json.gz`
with all original per-case observations, probabilities, decisions, errors,
both branch predictions, chaos evidence, seeds, and source/audit SHA-256
identifiers, **including every loss**. Checks reject changed digests, missing
seeds or scenarios, truncated tails, duplicate or reordered steps, and
mismatched replayed source forecasts. Full gzip round-trip is verified.

## What is actually measured

| Dimension | Observable proxy | Important limitation |
| --- | --- | --- |
| Alternatives | Both source-trust hypotheses predicted each time; disagreement rate, chaos gating and hindsight regret | Two programmed alternatives are not general reasoning |
| Evidence judgment | Pre-feedback source-reliability Brier loss vs subsequent sensor correctness, across 5 sources per tick | Requires host-provided truthful binary outcomes |
| Uncertainty | Prediction Brier, log loss, ten-bin calibration error, confident mistakes | Probabilistic calibration, not conscious uncertainty |
| Decision quality | Error rate, action-switch counts, cost-sensitive hypothetical utility | Switch penalties are assumed costs, not proven real-world harm |
| Learning | Early/late prequential errors and adaptation after source swap | Temporal differences are not causal proof of intelligence |

Every score is separate; **there is no aggregate intelligence or wisdom score**.
A lucky result is not proof of good ex-ante reasoning. The best alternative
chosen *in hindsight* is a descriptive comparison, not a fair reference
available when the agent acted. We do not measure wall-clock deliberation time.

## Locally reproduced results, 30 seeds × 120 rounds × 6 regimes

All 21,600 predictions were recorded before outcome feedback. Lower error is
better. The scenarios are reused synthetic families, NOT a fresh independent
holdout. Previous long-term / short-term comparators are unchanged.

| Decision policy | Prediction Brier | Wrong action rate | High-confidence mistakes | Calibration error |
| --- | ---: | ---: | ---: | ---: |
| Never learn sensor trust (fixed prior) | 0.22069 | 29.18% | 1,785 | 0.12952 |
| Always remember | 0.14253 | 20.88% | 1,264 | 0.09666 |
| Always forget (0.97 decay) | **0.11505** | **16.46%** | **914** | **0.05365** |
| Schrödinger's Logic (chaos only) | 0.11773 | 16.83% | 944 | 0.05425 |

Schrödinger's Logic evaluates both hypotheses on all 21,600 cases,
significant disagreement occurs in 2,193 cases and the selective parallel
mode triggers in 1,565 cases. Only 8 of those triggers occur outside the
source-swap condition. This is **not** proof that the other 1,557 triggers
were correct. The logic still loses overall to continuous forgetting.

Source reliability estimation over 108,000 sensor observations, Brier:
fixed prior 0.26352, long-term 0.19068, forgetting 0.18304. This assesses
the accuracy of *claimed source trust*, not merely the final decision.

In the source-swap condition, Brier over the first 10 cases after reversal:
long memory **0.85525**, always forgetting **0.78632**, dual-state **0.83101**.
Later post-swap (step 80 onward), errors improve to **0.50544**,
**0.08494**, and **0.12657** respectively. Dual-state adjustment is
real in this controlled test, but slower than continuous forgetting.

Comparing the first and last quarter of **all** simulations, dual-state
Brier changes from **0.10908** to **0.09421**, while fixed-prior changes
from **0.20122** to **0.23237**. The environments and state distributions
also change over time; these values do not prove a causal learning advantage.

## Next falsifiable tests

Challenge the model with missing feedback, incorrect feedback, spoofed
sensor origins, correlated sources, previously unseen distributions, and
nonbinary outcomes. Separately measure decision latency and the real-world
cost of reversing a correct belief. Do not optimize the fixed thresholds
against the same held-out scores and then call them independent.

**Outcome**: measurable evidence of source adaptation and conditional
hypothesis selection; *no verified AGI, broad reasoning, or autonomous
assessment of evidence truth*. Keep PR #199 draft and main unchanged.

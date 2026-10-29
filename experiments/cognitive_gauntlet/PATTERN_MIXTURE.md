# BEAN Cognitive Gauntlet: Bayesian pattern-mixture rematch

This is an **isolated BEAN experiment** in PR #199. It is not the Hyperon,
OpenNARS, PLN, Voyager, Letta or Dreamer runtime, nor a deployed Core change.

## What changed

The previous fixed volatility switch treated disagreements caused by ordinary
sensor noise as evidence of a changing world. `pattern_bayes.py` instead
computes the marginal likelihood of a constant hidden binary state versus a
state alternating each observation. A Beta(3,1) observation-reliability prior
is integrated for both hypotheses. The model then mixes BEAN's existing
source-aware revision and newest-observation predictions using the posterior
probability of alternation.

The resulting score is an experimental **prediction**, not a calibrated
probability or a claim of understanding. The model only reads observations,
evidence origin and confidence; no ground truth, scenario label, future sample,
or reward is passed into the policy.

## Frozen training parameters

The search considered windows 11, 15 and 21 and alternating priors
0.02, 0.05 and 0.10. Scored only on the original seeded synthetic training
environments (scenario seeds 0 through 19, 100 steps per seed).
The selected configuration was window **11** and prior **0.10**, retaining
Beta(3,1) reliability. Nothing is retuned on the evaluation samples.

## Local replay results

Mean squared error (lower is better). Full failures retained.

| Test split | Fixed revision | Newest-only | Previous adaptive | Pattern mixture | N |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original held-out seeds 20..79, three regimes | 0.180541 | 0.222833 | 0.153899 | **0.146130** | 18,000 |
| Additional synthetic seeds 400..439, eight regimes | 0.181397 | 0.269792 | 0.167976 | **0.162428** | 38,400 |

The additional eight regimes are a mixture of previously inspected stress
families and newly constructed variants. They are **not** an independent
external benchmark. These are *local* results; GitHub CI at the exact branch
commit is a separate check.

Noteworthy negative cases from the additional set:
- New noisy stationary: 0.271436 pattern mixture versus 0.263408 fixed
  revision, a **regression** versus the fixed baseline.
- New rapid clean alternation: 0.049976 pattern mixture versus 0.042083
  newest-only, a **loss** to that control.
- Original held-out stationary: 0.127267 pattern versus 0.124714 fixed
  revision, also a **regression**.

No external frameworks were run. Synthetic results do not establish AGI,
learned model weights, overall superiority, or operation on physical hardware.

## Reproduce exactly

```sh
python -m unittest bean.tests.test_cognitive_gauntlet bean.tests.test_cognitive_adaptive bean.tests.test_cognitive_stress bean.tests.test_cognitive_pattern -v
python -m experiments.cognitive_gauntlet.pattern_benchmark
```

The second command saves `cognitive-gauntlet-results/pattern-mixture.json.gz`,
including all 56,400 case-level inputs, forecasts, per-arm errors, scores,
parameter provenance and SHA-256 of the canonical unsigned JSON. Gzip is
losslessly round-tripped. The GitHub workflow uploads the evidence archive on
both Windows and Ubuntu, Python 3.11 and 3.12, **including failures**.

## Evaluation cautions

This prototype scores the current hidden value against an observation just
received; it is not a future-action planner. Sensor origins are asserted by
the test harness, not authenticated. Only binary observations have a
likelihood model; nonbinary inputs fall back to the original revision.
The old test environments informed the decision to try this architecture,
so those environments alone do not support independent generalization claims.
For stronger evidence, use an externally held, previously unexamined data
source and independently implemented real opponent systems on matched budgets.

The mainline BEAN Core, SpongeTD/DQN, local memory, Bridge and existing
real BEAN-versus-Aider arena are not modified or replaced.

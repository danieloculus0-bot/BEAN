# BEAN: source-provenance-aware evidence pooling

**Mainline research-only extension, 2026-10-29.** This extends the existing
`OnlineSensorTrust.forecast` API with optional `provenance_groups`, rather
than introducing another learner or changing Core's runtime behavior.

## Why

Five sensor reports are not necessarily five independent pieces of evidence.
If three sensors read the same upstream bus, their correlated votes can
overwhelm two genuinely independent sources. When the caller **knows** the
shared upstream provenance, `forecast(observations, provenance_groups=...)`
counts each group as one mean log-likelihood vote. The original
`forecast(observations)` is unchanged, as are the per-source Beta updates,
delayed outcome requirements, skip behavior and checkpoint schema.

Groups must cover every origin exactly, with nonempty bounded group IDs.
Invalid groups are rejected before evidence IDs are consumed. Unique groups
produce the unchanged baseline prediction. The caller asserts the grouping;
BEAN **does not discover, authenticate or independently verify** source
dependence. Incorrect grouping can degrade accuracy, so this is an opt-in
research capability, not a universal cure for correlated evidence.

## Evidence protocol

`python -m unittest bean.tests.test_cognitive_sensor_provenance -v`

`python -m experiments.cognitive_gauntlet.sensor_provenance`

The synthetic benchmark uses predeclared evaluation seeds 41000 through
41011, disjoint from exploratory design seeds 31000 through 31011.
There are six families: correlated shared bus, weak shared bus, independent
sources, falsely grouped independent sources, selective missing outcomes,
and two independent shared buses. Each case retains observations, asserted
groups, predictions, truth revealed only after prediction, squared errors,
feedback availability, trust counts and a canonical SHA-256 report digest.
The output is `cognitive-gauntlet-results/sensor-provenance.json.gz`.
The unchanged ungrouped learner and grouped learner receive identical
feedback and training counts. Missing outcomes never train either.

The deliberately wrong-group family is a negative control. Results are
synthetic and conditional on host-supplied grouping. A passing CI run is
regression evidence, not proof of transfer to unknown real-world sources,
BEAN Core autonomy, neural training, AGI or consciousness.

The original [Gauntlet PR #199](https://github.com/danieloculus0-bot/BEAN/pull/199)
and its branch and case receipts remain untouched. See
[SENSOR_RELIABILITY.md](SENSOR_RELIABILITY.md) for the unchanged baseline
and earlier independent missing-feedback failures.

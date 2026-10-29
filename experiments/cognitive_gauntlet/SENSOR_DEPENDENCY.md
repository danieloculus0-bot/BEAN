# Delayed-feedback dependency inference (opt-in research)

**Status:** isolated Python research adapter, not BEAN Core automatic cognition or authenticated source provenance. Reuses `OnlineSensorTrust`, its delayed binary feedback, missing-outcome receipts, and optional source-group pooling. Does not modify the underlying learner, production policies, or Gauntlet-owned branch.

## Question

Can BEAN infer when multiple supposedly independent signals are redundant **from past, verified, correlated mistakes** rather than blindly trusting host-supplied provenance labels? The candidate tracks bounded, exponentially decayed pairwise error co-occurrence. It requires at least 20 effective labeled observations, three effective joint mistakes, and excess joint-error probability of at least 0.10 above the product of marginal errors. Complete-linkage grouping requires every pair in a cluster to meet that criterion. It uses only previous feedback when forecasting. Missing feedback does not update dependence statistics.

This is a deliberately narrow heuristic. Correlated mistakes do **not** establish a common upstream source, and an adversarial or selectively missing feedback stream can defeat it. The adapter is not a verified causal-discovery engine. It raises when the configured 12-source/120-pair memory budget is exhausted rather than silently discarding observations.

## Evaluation and reproducibility

`python -m unittest bean.tests.test_cognitive_sensor_dependency -v`

`python -m experiments.cognitive_gauntlet.sensor_dependency_benchmark`

Six predeclared synthetic regimes use evaluation seeds 61000..61011 and 120 steps each (8,640 forecasts), with separate exploratory seeds 51000..51011. The same observations, feedback availability, source reliability learning, and budget are supplied to unchanged ungrouped baseline, delayed-feedback inferred grouping, and an **oracle grouping comparator** (the oracle is not available to BEAN). Scenarios include shared bus, independent sources, two buses, selective missingness, weak shared source, and correlation reversal. Original observations, evaluator truth, group decisions made **before** feedback, missingness, forecasts and squared errors are preserved as case-level gzip JSON with SHA-256 manifest digest in each CI artifact. No training occurs on heldout seeds across runs.

Exploratory local run using a minimal API-compatible sensor stub (not full GitHub Core): 5/5 tests passed, and 8,640-case MSE was 0.128972 ungrouped, 0.116069 inferred, 0.085074 oracle. In selective-missing feedback, inferred grouping **did not improve** (0.237541 vs 0.237541), while the unavailable oracle scored 0.104392. These are provisional local synthetic outcomes, **not** exact-source GitHub CI results. CI must confirm or falsify them at the committed source SHA. A favorable aggregate is not proof of robust cross-domain generalization, independent causal identification, AGI or consciousness.

## Restart-safe learning state (2026-10-29)

`OnlineDependencyLearner.state()` now snapshots a closed feedback boundary, the existing `OnlineSensorTrust` receipt history, learned pairwise co-error statistics, configuration and latest inferred grouping. `restore()` rejects malformed, duplicate, non-finite, out-of-budget and internally inconsistent pair data, and delegates underlying receipt integrity checks to the existing sensor trust restorer. No checkpoint is allowed while feedback is pending. Two additional regressions compare uninterrupted and restarted forecasts over a 90-step deterministic heldout with missing outcomes, and exercise tamper rejection. The original six-regime synthetic benchmark remains unchanged. This is restart continuity, **not** new predictive improvement or cryptographic provenance authentication; pair counts cannot be independently rebuilt from trust receipts because those receipts omit raw sensor values.

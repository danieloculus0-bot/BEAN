# Schrödinger's Logic: chaos-only dual-memory reasoning

**Experimental branch only.** Name proposed in BEAN development conversation.
The physics comparison is a metaphor. This uses ordinary classical Python
models, not qubits, quantum superposition or quantum computing.

## Hypothesis

When evidence is consistent, rely on long-term memory. When evidence becomes
contradictory, preserve both competing estimates and explicitly evaluate the
possibility that recent evidence is more relevant than old experience.

This experiment keeps two existing `OnlineSensorTrust` instances in parallel:
- **Remembering state:** all delayed feedback contributes to permanent Beta
  source-reliability counts (decay 1.0).
- **Forgetting state:** the same feedback updates a separate model using
  decayed Beta evidence (decay 0.97). Old receipts are retained even though
  old *weights* diminish.

Both models receive identical input and ground-truth feedback **after**
forecasting. During calm conditions, the output is exactly the long-memory
prediction. It consults both predictions in its output **only during chaos**.

## Chaos evidence and hysteresis

The decision to enter chaos uses no knowledge of the current answer.
It requires (a) enough past scored predictions, (b) a recent lead in
prediction squared-error by the forgetting model, and (c) meaningful
divergence between the models' source reliability estimates.

Frozen initial values (not fitted against the reported replay):
- Previous scored window: 12 outcomes, minimum 18 preceding trials
- Enter only if short-memory mean loss advantage >= 0.025 and mean
  per-source reliability gap >= 0.075
- Stay in chaos while advantage >= -0.005 and gap >= 0.035
- Chaos forecast: 20% remembering + 80% forgetting; calm: 100% remembering

These are *candidate heuristic constants*, not learned optimal settings.
The chaos status and both memory states are part of the restartable receipt.
The `SchrodingersLogic` model does not erase or overwrite evidence.

## Exact comparison

```sh
python -m unittest bean.tests.test_cognitive_schrodinger -v
python -m experiments.cognitive_gauntlet.schrodinger_benchmark
```

`schrodinger_benchmark.py` reuses the existing sensor benchmark's **exact**
original generated cases, controls, evidence IDs and delayed feedback.
It asserts the two underlying model predictions match the reference at
every case. Every event, baseline prediction, learned prediction, outcome,
error, chaos reason, seed and mode decision is stored in compressed JSON
at `cognitive-gauntlet-results/schrodingers-logic.json.gz`.
Its SHA-256 digest and byte-for-byte gzip round-trip are checked.
CI runs on Ubuntu and Windows under Python 3.11 and 3.12.

### Development-only local mirrored simulation (not certified CI)

A separate, formula-equivalent Python check of 30 seeds × 120 rounds × 6
synthetic environments (21,600 decisions), with frozen candidate constants,
gave mean squared error (lower better):

| Regime | Remember always | Forget always | Chaos-only dual state |
| --- | ---: | ---: | ---: |
| Diverse stable sources | 0.043372 | 0.043478 | **0.043372** |
| Adversarial but fixed sources | **0.035639** | 0.037701 | **0.035639** |
| Weak information | **0.269841** | 0.272043 | 0.269920 |
| Sensor trust reverses | 0.327938 | **0.157628** | 0.179018 |
| Rapidly changing truth | **0.040307** | 0.040844 | **0.040307** |
| Correlated sensor sources | **0.138104** | 0.138636 | **0.138104** |
| **Aggregate** | 0.142534 | **0.115055** | 0.117727 |

The model flagged 1,557 of 3,600 source-swap steps as chaos; only 8 of
18,000 steps outside the swap regime. It therefore largely avoided
false-positive switches on these synthetic data, **but missed part of the
adaptation opportunity during a real source reversal**. The chaos-only
method is better than permanent memory overall, yet slightly worse than
always forgetting. That is an **explicit negative result**, not a win.

A second formula-equivalent replay on separate seeds 9000 through 9029
also yielded 0.118064 (dual), 0.142803 (permanent) and **0.115778**
(always forgetting), with 1,547 swap-region chaos steps. Those seeds
were inspected during development, so they no longer count as pristine
held-out evidence. The authoritative repository implementation and tests
must still pass GitHub Actions at the exact revision.

## Boundary and next challenge

This prototype is narrow binary sensor classification with feedback after
every forecast. It does not work without enough trustworthy verified
outcomes; it does not independently authenticate source identity, handle
incomplete labels or detect every form of distribution change. Correlated
sources violate its underlying independence approximation.

Investigate shorter detection lag, outcome scarcity and feedback corruption
using a new preregistered seed distribution. Do not tune on the two
published samples while claiming they are unseen. The design is not AGI,
not an external-framework contest and not merged into BEAN main.

## Decision quality is not reaction speed

A deliberate, slower decision can be reasonable given the evidence available
at the time, even if it later turns out to be wrong. Conversely, a lucky
guess is not evidence of good reasoning. Switching quickly is **not** a
standalone objective, and a system that refuses to switch may be appropriately
skeptical or dangerously stubborn depending on its evidence.

The separate `decision_audit.py` now scores the existing **frozen** case
receipts, without changing or tuning the predictions. The benchmark embeds
the audit in its compressed receipt. It reports:

- Brier score and log loss, which reward honest probability estimates
  rather than simply counting correct binary choices
- Classification errors and high-confidence mistakes, separating
  justified uncertainty from confidently wrong predictions
- Descriptive 10-bin calibration error, with known sample-size sensitivity
- Decision changes separately from chaos-mode changes, without treating
  fewer changes as automatically better
- Sensitivity to hypothetical switching costs 0, 0.02 and 0.10, never
  presenting any one cost as a universal measure of intelligence
- Per-regime breakdowns, all cases retained, and an independent SHA-256
  audit receipt linked to the original sensor-duel digest

The audit requires contiguous case steps, identical arm coverage and
recomputed squared losses; missing, duplicate or corrupted cases fail
rather than disappearing from the average. It never sees labels before
the already-recorded forecasts. These are **retrospective evaluation
metrics**, not evidence that the predictor considered all options or
performed human-like deliberation.

Reproduce the metric unit tests with
`python -m unittest bean.tests.test_cognitive_decision_audit -v`.
The repository workflow also runs these tests on four Python/OS jobs.

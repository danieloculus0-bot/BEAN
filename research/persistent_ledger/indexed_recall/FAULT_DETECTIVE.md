# Lab 031: BEAN Factory Fault Detective, 3,000 new problems

**Status:** complete synthetic research trial; experimental branch, not production or deployment.

## What BEAN did

BEAN faces one hidden cause from eight possible synthetic machine faults: motor, drive, encoder, bearing, pneumatic, relay, sensor or power. Eight imperfect and overlapping diagnostic tests are available. BEAN chooses when to test, which diagnostic heuristic to use, and when to stop and identify the fault.

Correct diagnosis receives **+40**, wrong diagnosis **−40**, and each diagnostic incurs its fixed test cost. Diagnostic results are probabilistic and are generated independently of the learning policy. The hidden true fault is revealed to the evaluator only after BEAN decides.

The adaptive controller is an **actual tabular Q-learning implementation**, with temporal-difference updates (α=0.18, γ=0.97), exploratory training and a frozen holdout. It selects between prewritten "diagnose now", cheapest available probe, information-per-cost probe and discriminating probe. Its decision state includes the **live cumulative scoreboard** and posterior belief summary. It is *not* a trainable neural network or a full BEAN reasoning-model integration.

## Protocol

- Exactly **3,000 unique hidden-fault specimens**: 1,600 training, 400 development, 1,000 untouched final holdout.
- 3 training epochs over the same 1,600 training cases (**4,800 training attempts**, all retained).
- After each epoch, compare frozen policy performance on 400 development cases. Choose the best checkpoint by average diagnostic reward, then number correct, then earliest epoch.
- The final 1,000 cases have new deterministic seeds and a higher observation-noise mixture than training. Use the selected checkpoint with **no Q updates** on holdout.
- Evaluate all fixed comparison strategies on **the same hidden cases**.
- The diagnostic world is a synthetic likelihood table, not an industrial failure dataset. Even the exhaustive comparator can be wrong because observations are noisy.

## Development performance

| Checkpoint | Correct / 400 development | Mean reward |
|---|---:|---:|
| After epoch 1 | 186 | -9.082 |
| After epoch 2 | 171 | -11.18275 |
| After epoch 3, selected | 195 | -7.456 |

The second epoch regressed; it was recorded, not silently discarded. The third checkpoint was selected **before** evaluating the final holdout.

## Final frozen holdout

| Strategy | Correct / 1,000 | Mean probes | Mean reward |
|---|---:|---:|---:|
| Untrained, no diagnostics | 147 | 0 | -28.24 |
| Cheapest-four heuristic | 417 | 4 | -11.24 |
| Five information-per-cost probes | 470 | 5 | -9.051 |
| Five discriminating probes | 473 | 5 | -8.8657 |
| **BEAN selected Q-policy** | **503** | **5** | **-6.2576** |
| Exhaustive eight-test strategy | 530 | 8 | -8.9 |

BEAN improves measured average reward relative to every fixed listed comparison on this particular seeded holdout and identifies 33 more hidden faults than the information-per-cost five-test heuristic. That 33/1000 difference is descriptive, not yet an independently replicated or statistically established general advantage. BEAN still misdiagnoses 497/1000 cases. Exhaustive testing makes more correct diagnoses at the cost of three additional probes per case.

**GitHub CI:** [run 39543554426](https://github.com/danieloculus0-bot/BEAN/actions/runs/39543554426) passed Ubuntu and Windows, Python 3.11 and 3.12, including the independent rerun and cold-cache reconstruction.

## Durable compressed evidence

[Research archive for the tested source commit](../fault_detective_evidence/52b1f1285ecbcd7104f515cb2bd09db4a1f3215d/README.txt) (directory: `research/persistent_ledger/fault_detective_evidence/52b1f1285ecbcd7104f515cb2bd09db4a1f3215d/`).

- **30 gzip JSONL case batches** (4,238,178 compressed bytes total) and **30 individually hashed manifests**, in `ledger/archive/`.
- Exactly **3,000 recoverable original problem records**, one per unique fault. Each contains oracle truth after the episode, all training/dev/holdout attempts, each test choice, diagnostic result, score viewed before the decision, Q-state and Q hash changes, reward, and failures.
- `trained-policy.json.gz`: the saved frozen Q-policy, 2,280 compressed bytes; SHA-256 is recorded in `scoreboard.json`.
- `scoreboard.json`: all checkpoints, selected epoch, method comparisons and sample counts.
- The SQLite lookup cache is disposable and rebuilt from compressed archives. Full reconstruction after cache deletion succeeded in CI.
- `python research/persistent_ledger/indexed_recall/fault_detective.py --output fault-detective-results` regenerates the full synthetic experiment.
- `python research/persistent_ledger/indexed_recall/fault_detective.py --output fault-detective-results --verify` independently regenerates deterministic fixture outcomes, Q updates, all scores, and compares every archived case record.

This lab demonstrates **persistent, scored experience improving a narrowly defined diagnostic selection policy** for this synthetic distribution. It does **not** demonstrate real-world machine diagnostic accuracy, neural model weight training, general problem solving, autonomous invention of heuristics, or automatic use by BEAN's main runtime. Those remain separate, testable engineering goals.

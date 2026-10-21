# BEAN Sponge Breakout: persistent research scoreboard

Experimental Q-learning research from [BEAN Sponge PR #99](https://github.com/danieloculus0-bot/BEAN/pull/99).
Not merged into Core Main. The game is a deliberately simplified, synthetic Breakout environment, **not** pixel Atari and **not** a demonstration of transfer learning or algorithm self-improvement.

## Reproduction protocol (October 20, 2026)

Both runs use **3,000 training games**, seven checkpoints selected on **200 validation games**, and one **200-game final holdout** not used for checkpoint selection.

| Independent run | Learner RNG | Training game seeds | Validation seeds | Holdout seeds |
| --- | --- | --- | --- | --- |
| Original replay | 20261011 | 900000–902999 | 18000–18199 | 21000–21199 |
| New randomization | 20261020 | 1200000–1202999 | 40000–40199 | 50000–50199 |

The new run changes learner randomness and seed windows, **not** the Q-learning implementation, action-space physics, loss or promotion metric. Identical Windows and Linux results are cross-platform reproducibility, not two additional independent training randomizations.

## Permanent receipts

- [Versioned SHA-chained scoreboard](evidence/score_ledger.jsonl): small append-only JSONL, with run IDs, exact seeds, seven checkpoint validation scores, policy SHA-256, full-journal tip, final cold-versus-trained holdout results, and linked prior-entry hash.
- [Ledger verifier](ledger.py), [publisher](publish_ledger.py) and [tampering tests](test_ledger.py). A repeated run key with conflicting measurements is rejected instead of silently overwriting history. CI writes only the compact scoreboard to the experiment branch.
- [Windows/Linux CI runs and downloadable journals](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-sponge-breakout.yml): each run archives separate SQLite learning histories and results.json files. Artifacts may eventually expire; the small Git ledger stays in version control.
- [BEAN Core learning-lesson ledger](../../research/learning_ledger.jsonl) is a different document: it records evidence-backed research lessons, not each Breakout game.

To verify an existing scoreboard:

```bash
python -m experiments.sponge_breakout.ledger experiments/sponge_breakout/evidence/score_ledger.jsonl --expect-runs 2
python -m unittest experiments.sponge_breakout.test_bridge_sponge experiments.sponge_breakout.test_ledger -v
```

The immutable artifact identity is a hash over deterministic source text and data, not proof that the measured reward is correct. CI reports the exact Git revision and run ID; the ledger shows the analysis protocol and results. Learning journals and compressed checkpoints remain in CI artifact ZIPs.

## Interpretation boundaries

These experiments show policy updates produced by temporal-difference reward learning, checkpoint selection, durable scored memories, and cross-process journal recovery. They do **not** show BEAN developing a new algorithm, outperforming a separately implemented classical Q-learning comparator, or learning general intelligence. The replay and new randomization share the same simplified environment; further blind tasks and baseline arms remain necessary.

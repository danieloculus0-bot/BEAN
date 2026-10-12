# BEAN Sponge: show it a game, give it a score, preserve the evidence

**Status: experimental. No BEAN Sponge Breakout success is claimed until independent CI artifacts are reviewed.**

## Learning philosophy
A game adapter supplies observations, valid actions, a reward for each transition, and a terminal flag. Sponge updates its action values using temporal difference Q-learning. Raw training outcomes cannot determine promotion. Every evaluation checkpoint must be measured on a fixed validation set and recorded with a pre-file score, SHA-256 memory fingerprint, and append-only journal receipt. The best validation checkpoint is tested exactly once against an untouched seed set. An observed improvement in one game is not evidence of learning transfer or autonomous algorithm invention.

## Reproducible experiment
```bash
python -m pip install numpy
python -m experiments.sponge_breakout.train --out sponge-breakout --episodes 3000
```
The command uses the actual `bean.optimization.sponge_td.SpongeTD` and `Journal`, not a simulated BEAN history. No API keys required. Uses 3,000 seeded training games, 200 validation games per checkpoint (0, 500, 1000, 1500, 2000, 2500, 3000), and an untouched 200-game final evaluation. Different seed ranges prevent direct evaluation leakage. A separate evaluation job should independently reproduce the verdict before promotion.

## Acceptance and failures
- Persist all checkpoint metrics, memory digest, mnemonic, scoring metadata, and journal tip; never discard losing trials from the audit trail.
- The score derives from independent performance measurements, sample counts, relevance/provenance evaluation where available. A host-supplied SHA only confirms local integrity, not evaluation independence.
- Reject corrupt or unscored capsules. Keep low-performing memories available for diagnostics without automatically adopting them as policy.
- Compare trained policy to cold and matched baseline Q-learning and repeat across independent training RNG seeds; require superiority on held-out environments before claiming meaningful net improvement.
- Check whether the final policy regresses relative to the highest validated checkpoint.
- Publish negative outcomes and resource consumption. Do not merge to Main or describe a performance gain from a green protocol test alone.

## Recorded results before Sponge integration
An earlier standalone Q-learning parameter-search pilot showed +0.16 bricks/game on 800 paired holdouts for one training seed. A three-seed replication subsequently yielded -0.26, 0, and 0 bricks/game relative to fixed configuration; mean -0.0867. Thus **there is no replicated parameter-search advantage**. See `docs/breakout-multiseed-replication-20261011.md`.

## Next qualification
Windows and Linux evaluation of SpongeTD, memory capsule integrity and journal restoration, independent multiple-seed runs, unchanged baseline comparison, then engineering review. This research is intentionally isolated from production systems.

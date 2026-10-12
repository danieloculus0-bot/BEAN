# BEAN Neuroevolution: Evolve the Learner, Not Just the Score

Status: **EXPERIMENTAL, UNVERIFIED HYPOTHESIS.** No net advantage from evolution has been demonstrated at the time of writing.

## Objective

The experiment does not claim to reproduce DeepMind's pixel-input Atari DQN. BEAN uses an engineered three-dimensional Breakout state. The question is more ambitious and directly measurable: **can BEAN improve its own learning configuration and preserve better neural weights across generations, beating an uninterrupted DQN given the same environment-episode budget?**

## Mechanism

1. Initialize a small **population** of trainable deep-Q neural networks. Each learns through actual stochastic-gradient updates with replay memory, a target network, and epsilon-greedy exploration.
2. Train all individuals on deliberately separated training-game seeds.
3. Evaluate each policy against **validation-only** seeds, using bricks per game as fitness. Secondary survival is reported but cannot silently override the declared fitness.
4. BEFORE archival, issue a BEAN `score_memory` evidence grade; put the neural weights through scored, lossless, compressed SHA-256 memory capsules. Append the score, parent hash, selected configuration and receipt to BEAN's existing tamper-evident Journal for successes **and failures**.
5. Select the best scored parent, **inherit** its trained weights, and create a next generation of unmutated and mutated children. Mutations modify learning rate, discount factor, exploration floor, and neural weights. Children continue training from inherited weights, **not random initialization**.
6. Preserve every candidate and complete lineage. Select the best over all generations by validation performance; do not look at holdout results during selection.
7. Compare the selected evolved model on sealed final seeds against both a cold baseline and an **uninterrupted DQN trained for the same total number of game episodes with the same seed multiset**. Record frames and gradient updates because equal episodes do not guarantee matched optimizer compute.

## Experiments

```bash
python -m pip install numpy
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m unittest experiments.sponge_breakout.test_evolve -v
python -m experiments.sponge_breakout.evolve --out evolution-evidence --seed 41 --population 3 --generations 3 --games 70 --validation 60 --holdout 120
```

The CI workflow `.github/workflows/bean-neuroevolution.yml` runs bounded smoke tests on Windows and Ubuntu. A commit with `[evo-replicate]` activates **three independent training seeds** after the smoke gate; it cannot automatically merge to Main.

## Falsification criteria

- Strong validation fitness but regression on sealed holdouts is failure, not evolution.
- Better than cold DQN yet worse than the budget-matched uninterrupted DQN is **learning**, but **no demonstrated evolutionary gain**.
- A single seed win is an observation, not an established net advantage. Repetition, paired holdout estimates, performance dispersion, and failure frequencies are required.
- Compressed memory SHA validates bytes, not measurements; host-attested evidence is not independently verified.
- The population shares common environment seeds inside each generation. This is a controlled search, not a demonstration of transfer beyond the original game. Pixel-input learning and adaptation to new environments remain future experiments.
- Memory is recorded but only tested policies can qualify for promotion. Production systems, wallets, hardware and Main are untouched.

## Baseline evidence

The previous actual BEAN SpongeTD (tabular Q-learning) scored **11.305** bricks per game vs **1.355** untrained on 200 held-out game seeds in both Windows and Ubuntu, with the same seed/training setup. This shows **within-task learning**, not superiority of neuroevolution. The prior six-way standalone hyperparameter search lost its advantage when rechecked across training seeds. See `docs/breakout-multiseed-replication-20261011.md`.

## Publication gate

Publish raw experiment receipts even if inconclusive. Claim "BEAN evolved a better learner" **only** after independent-seed testing shows a reproducible out-of-sample benefit over the matched standard DQN control, without material negative transfer. Never call a passing code unit test an agent intelligence breakthrough.

# Preregistration: independent non-Breakout reward-shift adaptation diagnostic (2026-10-12)

Status: **unrun at registration**. Research-only, no Main merge. Independent from BEAN Breakout seeds 65–67; branch pinned to annealed source commit `03cae7a4cd22cc4d1baa318d5b41a02b3fcb0316`. Synthetic contextual-bandit seeds **2001, 2002, 2003** are dedicated to this diagnostic; these are not Breakout seeds. Treat them as observed after execution.

## Falsifiable question
Can the existing three-input DQN adapt to a changed reward mapping after previously learning a conflicting mapping, as opposed to merely changing neural weights? Same initialized learner is compared before and after the task change. A frozen post-change copy is the paired control. An independent DQN trained with uncorrelated rewards is a negative control. This test does **not** demonstrate generalized intelligence, autonomous software repair, or improvements to the neuroevolution Breakout learner.

## Frozen fixed protocol
For each seed, one-step contextual bandit states contain `(x, binary_flag, binary_distractor)` with `x` uniformly in 0–14. Three actions. Rule A correct action is `(x // 5 + binary_flag) % 3`. Rule B correct action is `2 - rule_A`. Reward +1 for correct action, -1 otherwise, terminal transition after every step. The distractor carries no reward information. Train DQN on A for **2400 interactions**, then B for **1800**. Use `batch_size=32, warmup=64, learn_every=2, replay_capacity=5000, target_sync=100`; Adam default lr 0.0007, gamma 0.99, epsilon 0.15 throughout. Same network architecture as the source DQN; no evolution, shaped reward, or model search.

A copy of the A-trained policy must be evaluated on B without further updates (frozen control). Track B validation accuracy at **0, 300, 600, 900, 1200, 1500, 1800** post-switch interactions using a fixed, repeatedly viewed 300-context diagnostic set (not a held-out confirmation set). Separately train a fresh DQN for 1800 interactions on context-independent random correct labels; evaluate it against independently generated random labels.

Exactly one final previously unopened **600-context** paired evaluation set per seed for A-trained frozen, B-adapted and a cold model; separate independent 600-context labels for noisy-reward control. Final samples use dedicated seed domain 70_000 + seed for contexts, while training uses 10_000 + seed and validation uses 50_000 + seed. All seeds specified ahead of execution. No outcome-dependent stopping or hyperparameter adjustment.

Primary per-seed outcome: B-adapted accuracy minus frozen B accuracy on the final paired set. Secondary: A-trained accuracy on A, cold accuracy, negative-control accuracy vs chance 1/3, validation learning curve, frame/update counts and model fingerprints. Report each seed, arithmetic mean, sample SD, Student-t 95% CI at n=3 and all failures. Treat different OS repeats as reproducibility checks, not additional independent seeds. No statistical significance assumed and no promotion gate or Main merge based on this diagnostic alone.

## Execution
Pure Python task generator and validation assertions first on Windows and Linux (Python 3.12, CPU PyTorch). Only after both pass does independent matrix run 2001–2003 on Ubuntu. Preserve JSON and logs even if scores are poor. No opened Breakout holdouts are accessed. No code tuning after the final evaluations are viewed; any further change is a preregistered new experiment on new task seeds.

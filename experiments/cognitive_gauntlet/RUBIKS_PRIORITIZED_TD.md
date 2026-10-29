# BEAN-native prioritized TD replay for 3x3 cubes

Status: **experimental, not a general Rubik's Cube solver**. No result should be
promoted without exact-commit test receipts and disjoint held-out comparisons.

## Question

Can BEAN's existing SpongeTD learner propagate terminal reward through its
**own observed legal transitions** more effectively by replaying transitions
with high Bellman error, instead of uniformly random replay?

This is a **learning-order** experiment, not a reference-solver comparison.
The baseline and candidate have the same initial SpongeTD Q table, identical
canonicalized self-play transition graph, identical number of additional TD
updates, same frozen two-transition controller and same test puzzles.
The only changed variable is transition selection during extra training.

Candidate prioritization uses `abs(reward + gamma * max(Q(next)) - Q(state, action))`.
It queues predecessors when a state's best value changes. If no nonzero
residuals remain, it uses ordinary seeded replay to finish the matched update
budget. Both useful and filler updates are counted. No inverse scramble,
cubejs, external solver, solution teacher, or held-out outcome is fed to
training or inference.

## Reproduce

```bash
python -m unittest bean.tests.test_cognitive_rubiks_prioritized_td -v
python -m experiments.cognitive_gauntlet.rubiks3_prioritized_td --test-seed-start 7000 --output cognitive-gauntlet-results/rubiks3-priority-7000.json
python -m experiments.cognitive_gauntlet.rubiks3_prioritized_td --test-seed-start 8000 --output cognitive-gauntlet-results/rubiks3-priority-8000.json
```

Training seeds: 0 to 49. Held-out cohorts: 7000 to 7009 and 8000 to 8009.
Each cohort evaluates original 3, 4, 5, 6 and 20-turn scrambles.
Canonical states under the 24 proper cube rotations exclude train overlap and
holdout duplicates. No new data from either cohort may be used to retune this
experiment and still call the same cohort an independent holdout.

JSON receipts preserve each original scramble, legal starting state, each
BEAN-produced move sequence, both failure reasons, rotation-class exclusions,
Q-table hashes, training episodes, matched update counts and independent
solved-state replay. The policy is not allowed an arbitrary solution-move
ceiling; it stops on a cycle or missing positive learned value. A
half-turn-metric shortest solution is **not established** by this experiment.

## Decision rule

Compare candidate and unchanged baseline on **all eligible held-out states**,
including 20-turn failures and reverse regressions. Do not call the candidate
better solely because its training Bellman error is smaller. Do not merge a
regression or describe this as BEAN mastering the cube. An algorithm-inspired
microbenchmark is not a head-to-head win against OpenNARS, Hyperon, PLN,
Voyager, Letta or DreamerV3, none of which runs in this experiment.

Production BEAN cognition and the mainline developer's files are unchanged.

## First matched-update result and independent low-budget falsification

The first two cohorts, seeds 7000 to 7009 and 8000 to 8009, used eight
initial epochs and 4,000 additional updates per arm. On 90 eligible states
(10 excluded), **both** unchanged random replay and prioritized replay solved
35/90. Candidate better: 0; candidate worse: 0; 20-turn solved: 0/20.
The four isolated priority CI jobs passed at the first exact-head run
[40856126221](https://github.com/danieloculus0-bot/BEAN/actions/runs/40856126221).
This is a **negative finding**, not an improvement.

A separate, preregistered **sample-efficiency** test now uses one initial
epoch and 200 additional TD updates per arm, on two fresh, untouched cohorts:
seeds 9000 to 9009 and 10000 to 10009. It tests whether priority matters
before both methods have had thousands of backups. These new cohorts are not
reused from the first negative result, and the first negative receipts remain
unchanged. The low-budget outcome is unknown until exact-commit CI completes.

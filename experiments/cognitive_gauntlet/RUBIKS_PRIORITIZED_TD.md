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
It queues predecessors when a state's best value changes, and also requeues
the just-updated transition when a fractional TD learning rate leaves residual
error. If no nonzero residuals remain, it uses ordinary seeded replay to finish
the matched update budget. Both useful and filler updates are counted. No inverse scramble,
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
unchanged. The low-budget results are **33/95 candidate solved versus 27/95 baseline**
across 95 eligible held-out states (5 excluded): cohort 9000 was 15/50
versus 13/50; cohort 10000 was 18/45 versus 14/45. Six additional
independently replayed solutions, zero reverse regressions, and **0/20
20-turn states solved**. All four isolated priority jobs passed at
[exact-head CI 40856372962](https://github.com/danieloculus0-bot/BEAN/actions/runs/40856372962)
on Ubuntu/Windows with Python 3.11/3.12. Per-cohort SHA-256 receipts
matched across platforms. This is a **small sample-efficiency improvement**
at a reduced TD budget, not general cube mastery or evidence of shorter
optimal solutions.

## Fractional-alpha priority correction (2026-10-29)

Earlier priority replay did not requeue the just-updated transition. With
`alpha=1` this was harmless for the terminal edge, but fractional TD rates
could leave positive Bellman error and prematurely use random filler updates.
The correction requeues that edge after each partial backup and adds a
five-update, `alpha=.25` regression test with an analytic expected Q value.
Existing cube benchmarks use `alpha=1`, so their previously reported matched
holdout results are not retroactively changed. This is a learning-scheduler
correctness fix, **not** evidence of new 20-turn solving ability. Exact-head
cross-platform CI must pass before treating the correction as verified.

## Preregistered fractional-rate comparison

The experimental workflow now runs two additional disjoint held-out cohorts,
seeds 11000 to 11009 and 12000 to 12009, with `alpha=.25`, one initial
training epoch, and 200 matched additional TD updates per arm. This probes
whether repeatedly reprioritizing partially updated transitions improves
BEAN's sample efficiency when `alpha<1`. The unchanged uniform-replay arm
receives the same self-play graph and update budget. Original scrambles,
exclusions, failures and both policies' move sequences are archived in
separate JSON artifacts. **No result is claimed until exact-commit CI runs.**

Neither arm receives inverse scramble recipes or reference-solver answers.
The 20-turn solve criterion and shortest-HTM evidence requirements are
unchanged. This experiment must not be described as a general cube solver.

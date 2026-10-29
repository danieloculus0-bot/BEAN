# BEAN-native joint-goal hotter/colder experiment

Status: **experimental, not a general cube solver**. The previous frozen
joint-Q continuation did not produce any additional 20-turn solutions.
This experiment changes **learned weights**, rather than merely changing
how existing weights are read.

## Hypothesis

BEAN's original 96 corner-edge pair learner receives +1 only when both
pieces become jointly solved. It does not learn much from useful intermediate
configurations. Train an otherwise identical BEAN SpongeTD learner with a
discounted local closeness change for each pair, retaining the original +1
for a newly solved pair. This is a *local reward heuristic*, not an oracle
for whole-cube distance or a proven policy-invariant shaping transformation.
The goal is to test whether denser feedback improves independent full-cube
solves without teaching inverse scrambles.

The local potential is `1/(1 + corner_distance + edge_distance)`, with
the pair's terminal successor potential set to zero. Preserving a
already completed pair is explicitly neutral; disturbing it is penalized.
The shaping term is
`0.5 * (gamma * successor_potential - current_potential)`. A completed
pair earns the original +1 only on first completion; simply remaining
completed does not repeatedly earn +1. Learned joint action values are
passed into the existing `policy_solve_joint_rescue` controller, using
its same one-successor backup and same frozen full-state fallback.

## Paired controls and evidence

Both joint learners see the same observed legal self-play transitions,
in the same seeded order, and receive the same number of SpongeTD updates.
The unchanged baseline uses the original terminal-only `train_pairs`
reward. Both share an identical frozen full-state policy and use identical
inference compute slices. Different reward content is the **only**
joint-training difference. This matches update counts, not computational
expense or representation complexity.

Train seeds 0-15, lengths 2-6. Predeclared independent holdout cohorts
33000-33004 and 34000-34004, lengths 3, 4, 5, 6, 20.
Exclude rotation-equivalent training states and duplicate heldout states.
All original evaluator-only scrambles, legal starting states, routes,
per-case failures, pauses, checkpoint digests, source revisions and
unchanged controls are retained. A paused attempt is not a definitive
failure. A 64-action slice bounds one invocation's computation, **not**
the total solution length. Every route is independently replayed and
the receipt checker rejects forged success flags even if its JSON digest
is recomputed.

Reproduce:

```bash
python -m unittest bean.tests.test_cognitive_rubiks_joint_temperature -v
python -m experiments.cognitive_gauntlet.rubiks3_joint_temperature --test-seed-start 33000 --output cognitive-gauntlet-results/joint-temperature-33000.json
python -m experiments.cognitive_gauntlet.rubiks3_joint_temperature --verify --output cognitive-gauntlet-results/joint-temperature-33000.json
python -m experiments.cognitive_gauntlet.rubiks3_joint_temperature --test-seed-start 34000 --output cognitive-gauntlet-results/joint-temperature-34000.json
python -m experiments.cognitive_gauntlet.rubiks3_joint_temperature --verify --output cognitive-gauntlet-results/joint-temperature-34000.json
```

The reference solver and inverse scramble are absent from both training and
inference. This is a BEAN-only algorithmic microbenchmark, **not** a direct
OpenNARS, Hyperon, PLN, Voyager, Letta or DreamerV3 runtime comparison.
A full 20-turn solution or shortest half-turn-metric result must be
independently verified before claiming it. Never treat a CI pass as a
performance improvement without inspecting actual heldout counts.

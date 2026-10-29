# BEAN cube policy experiment (isolated, reproducible)

This folder contains the first **BEAN-native learned-action policy** for a legal
3x3 Rubik's Cube. It reuses the mainline `SpongeTD` temporal-difference
learner and legal 18-move facelet transitions. The policy sees the scrambled
state, **not** the scramble trace or a conventional solver's answer. Training
uses self-play transitions and rewards only reaching the solved state.
Inference follows frozen learned Q-values and one-step value transfer; it
does not call the conventional solver. It stops on a missing learned action
or repeated state, not a fixed solution-move limit.

Run:

```bash
python -m unittest bean.tests.test_cognitive_rubiks3 bean.tests.test_cognitive_rubiks_sponge -v
python -m experiments.cognitive_gauntlet.rubiks3_sponge
```

The runner saves full case-level JSON, failed attempts, seed/length exclusions,
Q-table hash, solved-state replay and conventional bounded-search comparisons.
A compressed scored BEAN SpongeTD policy is saved in a hash-chained SQLite
journal and reopened in the tests to verify restored behavior. GitHub Actions
archives both files. The conventional search in `rubiks3.py` is a comparator
and a geometry test, **not** BEAN's learned policy.

**Initial local Linux results**, 250 self-play seeds and 50 predeclared heldout
cases: 2 duplicate/overlapping states excluded, leaving 48 unseen starts.
The BEAN-native policy independently solved 7/48, matching the proven shortest
HTM solution in those 7. It solved 5/8 three-turn and 2/10 four-turn scrambles,
but **0/10** each at 5, 6 and 20 turns. The untrained policy solved 0/48.
Unchanged bounded search solved 38/48 at depth 6; this is not an arbitrary
solution limit on the learned policy.

These results show narrow, real TD learning and transfer, **not** a general
3x3 solution capability, production BEAN Core integration, or AGI. The public
browser challenge at [docs/rubiks-cube.html](../../docs/rubiks-cube.html)
remains a separate cubejs reference and route-memory demonstration. Do not
attribute its solutions to BEAN's learned policy. Exact-commit GitHub Actions
results must be inspected separately from local tests.

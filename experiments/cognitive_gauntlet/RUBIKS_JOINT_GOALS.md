# BEAN native joint-cubie subgoal learning

Status: isolated research, **not a full-cube solver**. The prior independent
cubie learner solved 0/88 held-out states against 17/88 for unchanged
rotation-equivariant SpongeTD, including 0/20 full 20-turn scrambles. The
next falsifiable hypothesis is that learning a *joint* corner-and-edge goal
will improve transfer by capturing some interactions that single-piece
action values cannot represent.

This experiment reuses the existing BEAN SpongeTD implementation, cube
legality checks, legal self-play transition graph, piece identity features,
canonical state exclusion, and learned-value rollout comparator. It learns
96 labeled corner-edge joint action-value tables per observed transition.
Reward +1 is delivered only when **both** pieces in a pair become solved
on that transition. Keeping an already completed pair solved earns zero,
preventing repeatable reward harvesting. Single-piece progress earns no
joint terminal reward. This is a narrow
representation experiment, not a general planner or an external solver.

The candidate is an actual learned Q-value action controller. At inference
it sees only the scrambled legal facelet state and its frozen learned joint
Q table. It chooses each legal face turn using the aggregate of 96 joint
values. It never reads the scramble recipe, inverse, cubejs, or reference
search. It stops on a cycle or when no positive learned action remains.
For runaway prevention, each invocation has a 128-action **compute slice**.
An unfinished attempt is recorded as **paused**, with a serialized starting
state and complete legal route. It can resume on a later invocation with
\`policy_solve_pairs(learner, start, checkpoint=receipt, work_budget=128)\`.
This is not a final solution-move cap, and paused cases are not completed
failures. Independent replay still checks the partial route.

## Matched comparison

The unchanged comparator is BEAN's rotation-equivariant full-state SpongeTD
policy with the existing two-transition value controller. Both arms use
the same legal self-play source. The comparator receives extra random TD
replay to match the candidate's **number of SpongeTD.learn calls**. This
matches update count, not representation size, reward information or compute
cost. We must not describe this as equal computational expense.

Training seeds: 0 to 15, scramble lengths 2 through 6, two epochs.
Predeclared new holdouts: 22000 to 22009 and 23000 to 23009, lengths
3, 4, 5, 6, 20. Exclude states rotation-equivalent to training states
or previously scored heldouts. Record all exclusions, original evaluator-only
scrambles, state facelets, learned Q hashes, policy moves and counts, failures,
pair feature coverage, and independent solved-state replay. Keep 20-turn
outcomes separate and do not claim shortest half-turn metric paths.

Run:

    python -m unittest bean.tests.test_cognitive_rubiks_pair_goals -v
    python -m experiments.cognitive_gauntlet.rubiks3_pair_goals --test-seed-start 22000 --output cognitive-gauntlet-results/rubiks3-pairs-22000.json
    python -m experiments.cognitive_gauntlet.rubiks3_pair_goals --test-seed-start 23000 --output cognitive-gauntlet-results/rubiks3-pairs-23000.json

Do not retune this candidate using the two holdouts and still call them
independent. Compare **all** eligible cases, including reverse regressions.
A successful joint two-piece controller does not establish coordination of
all twenty pieces or general 3x3 mastery. This is a BEAN-only algorithmic
microbenchmark, not a direct comparison against OpenNARS, OpenCog Hyperon,
PLN, Voyager, Letta, or DreamerV3. No mainline production changes.

## Results

Pending exact-commit CI execution and artifact review. Do not promote a
performance claim or full-cube notification until the receipts are checked.

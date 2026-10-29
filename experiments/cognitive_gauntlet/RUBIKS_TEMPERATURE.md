# BEAN 3x3 hotter/colder reward experiment

Status: experimental BEAN-native SpongeTD learning, **not** full-cube mastery.

## Hypothesis

The previous learner received only +1 when an entire 3x3 cube was solved and
zero for other moves. That makes reward sparse for 20-turn scrambled cubes.
Test the user's "hotter/colder" proposal: can BEAN learn more from the legal
geometry of the current state without a solution teacher?

For each of the 12 edges and 8 corners, enumerate the 24 legal
position/orientation configurations under the 18 permitted half-turn-metric
face moves. BFS on each **individual cubie** yields a distance to its solved
position/orientation, deliberately ignoring interactions among other cubies.
The sum is an informative *temperature*, **not** exact full-cube solution
distance. The code uses the already existing facelet simulator and physical
cube validator. No external solver or inverse scramble supplies the values.

Define Phi(s) = -(sum of 20 cubie distances)/8. The raw
hotter_colder(before,after) signal is positive if this potential increases,
negative if it decreases, and zero for equal temperature. This signal is
available for inspection but is not directly used as the TD reward because
naive delta rewards can encourage loops or alter the target policy.

Instead, candidate SpongeTD training uses potential-based shaping:

    r'(s,a,s') = r_terminal(s,a,s') + gamma * Phi(s') - Phi(s)

The terminal reward remains +1. With Phi(solved)=0, the discounted shaping
terms telescope to a constant for all complete paths from the same starting
state, preserving their discounted-return ordering. For gamma < 1 a
temperature-neutral step can have a nonzero *shaped* reward; do not confuse
that with the raw hotter/colder signal. Intermediate negative feedback does
not necessarily mean a move is strategically wrong: setup moves may be needed.

## Controlled experiment

The unchanged baseline uses terminal-only reward, and the candidate uses
the shaped reward. Both reuse the same BEAN SpongeTD implementation,
rotation canonicalization, **identical sampled self-play states and legal
edges**, seeded replay order, TD learning rate, discount, number of updates,
and unchanged two-transition learned-value controller. The only changed
variable is the reward signal. Neither arm receives cubejs answers, reference
routes, or inverse scrambles. This is a native learned-Q comparison, not
a comparison against OpenNARS, Hyperon, PLN, Voyager, Letta or DreamerV3.

Preregistered untouched holdout seeds: 13000 to 13009 and 14000 to 14009,
with 3, 4, 5, 6 and 20-turn legal scrambles. Training uses seeds 0 to 49
and exploration lengths 2 through 6. Exclude rotation-equivalent overlap
with training or prior holdout cases. Preserve every original scramble
(evaluator-only), legal state, selected route, independent replay result,
move count, failure, exclusion, source revision and Q-table hash. No arbitrary
solution-move ceiling exists; inference stops on cycles or lack of positive
learned values. No shortest-HTM claim is made.

Reproduce:

    python -m unittest bean.tests.test_cognitive_rubiks_temperature -v
    python -m experiments.cognitive_gauntlet.rubiks3_temperature --test-seed-start 13000 --output cognitive-gauntlet-results/rubiks3-temperature-13000.json
    python -m experiments.cognitive_gauntlet.rubiks3_temperature --test-seed-start 14000 --output cognitive-gauntlet-results/rubiks3-temperature-14000.json

Evaluate **all** eligible holdouts, including reverse regressions and 20-turn
failures. Do not retune using these cohorts and still call them independent.
The shaped reward may improve, tie or worsen performance. It cannot by
itself generalize the tabular policy to every previously unseen state;
piece-factorized control or learned subgoals remain separate hypotheses.

No Core runtime, public cube page, or mainline cognition behavior changes.


## First result: naive use of shaped Q values failed

On the original preregistered holdouts 13000 and 14000, Linux Python
3.11/3.12 CI reproduced a decisive negative result at commit
325b066e9b5b38378ecd41bd15b17ec8b7eaef34:
- 13000: 45 eligible, 5 excluded; terminal-only 19 solved, shaped 0 solved,
  19 reverse regressions; 0/10 full 20-turn cubes.
- 14000: 47 eligible, 3 excluded; terminal-only 18 solved, shaped 0 solved,
  18 reverse regressions; 0/10 full 20-turn cubes.

The learned Q values trained with potential shaping represent Q'(s,a), not
ordinary Q(s,a). Feeding Q' directly into the unchanged value controller
is a mismatch: potential shaping shifts every state-action value by -Phi(s).
The initial experiment deliberately preserved this failure instead of
silently rewriting it. All individual case receipts remain in the original
CI artifacts. Passing unit tests alone did not establish a good policy.

## Corrected interpretation, separately tested

The follow-up hypothesis applies the algebraic correction
Q(s,a) = Q'(s,a) + Phi(s) before using shaped values for action selection.
It still uses the same two-transition BEAN learned-value controller, the
same legal rules and the same matched SpongeTD update budgets, with no
external solver. This corrects interpretation of the trained values; it
does **not** add a full-cube distance oracle or solve unseen states by search.

The corrected candidate is evaluated on **new, untouched cohorts 16000 and
17000**, never on the already-observed 13000/14000 cohorts as if fresh.
A separate small 15000 cohort tests basic integration. The baseline remains
the original terminal-only learner. Both failures and improvements count.
No generalization or 20-turn success is claimed until exact-head CI receipts
are inspected.


## Corrected fresh-holdout result (2026-10-29)

The potential-corrected controller passed all eight temperature tests on
Linux Python 3.11 and 3.12 at run
https://github.com/danieloculus0-bot/BEAN/actions/runs/40872267768 .
On disjoint untouched 16000/17000 cohorts:

- 16000: 45 eligible, 5 excluded; unchanged baseline 19 solved,
  potential-corrected shaped learner 19 solved; 0 better, 0 worse; 0/10
  20-turn cubes.
- 17000: 49 eligible, 1 excluded; unchanged baseline 17 solved,
  potential-corrected shaped learner 17 solved; 0 better, 0 worse; 0/10
  20-turn cubes.

**Combined 36/94 versus 36/94, with 0/20 full 20-turn solves.**
This is a valid negative result. The shaped reward provided more intermediate
feedback, but did not create new state coverage or longer-range generalization
in this matched training setting. The naive raw-value controller's 0/92
failure remains separately preserved, not erased by this correction.

The next experiment should isolate *learned piece-level value transfer* or
reusable subgoals on states outside the tabular Q graph, rather than another
whole-state replay scheduler. Any such proposal must be compared on new
independent holdouts. Do not promote this reward shaping as a solving gain.

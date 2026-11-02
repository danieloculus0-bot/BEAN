# BEAN: Fake It Till You Make It (experimental)

The premise: a deceptive claim or an unconventional shortcut can be a rational
**tactic** without being a completed **result**. BEAN should learn where bluffing
pays, where it backfires, and where doing the work is the best option.

This is executable, isolated *synthetic game learning*, not a live capability
to deceive people, falsify test results, or bypass production controls.

## What BEAN learns

We reuse the real mainline SpongeTD tabular Q-learner, not a renamed heuristic.
Each independent game gives three public signals: probable audit strictness,
whether an alternate route is open, and whether resources are available to
build. Four available strategies:

- **Honest build:** do the work when resources are available; otherwise fail
  transparently, with a small penalty.
- **Bluff then build:** falsely claim early progress, then actually finish
  if the bluff survives scrutiny **and** resources permit building. This can
  outperform honest work in a lenient environment but is costly under strict
  audits or unavailable resources.
- **Bluff only:** show apparent success without delivering. This can earn
  *positive tactical reward* under lax scrutiny, especially if unable to
  build, but never counts as genuine completion. A caught bluff is costly.
- **Loophole:** use a different route. High payoff when available, failure
  when the route is closed.

Actions are offered by the experiment designer. BEAN *learns selection among
them from reward*, not new action primitives or general deception concepts.

## Evaluation

All policy choices see only public signals. Audit draws, actual audit
conditions, and true outcomes remain with the environment until settlement.
A separate evaluator scores actual task delivery, claimed success and payoff
as **three separate variables**. Successful deception can have real game value
without the judge falsely recording completed work.

Training, validation, ordinary holdout and *unannounced strict-audit shift*
have disjoint seeds. Every trial and failure is preserved in lossless,
deterministic compressed JSONL. BEAN's learned Q-table is SHA-verified through
its original scored checkpoint/restart path, without deployment to BEAN Core.

Holdout comparisons include BEAN's frozen learned policy, cold Q learner,
always honest, always bluff-then-build, always bluff-only, always loophole and
uniform random. Report real delivery, false claims and reward separately.
The audit shift deliberately tests the failure of a learned bluffing policy
when apparently safe opportunities turn dangerous.

## Reproduce

    python -m unittest bean.tests.test_strategic_bluffing -v
    python -m experiments.strategic_bluffing.lab --output strategic-bluffing-results

Read the generated scoreboard.json and lossless events.jsonl.gz. These runs
do not prove general intelligence, strategic creativity outside this game,
or successful manipulation of a real external judge. Do not interpret
claimed success as actual success.

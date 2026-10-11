# Lab018 measured outcomes — same questions, fresh questions, three paths

**Execution evidence:** [dedicated six-job Linux/Windows CI run 38104856084](https://github.com/danieloculus0-bot/BEAN/actions/runs/38104856084) (6/6 passing) and [full Core run 38104856034](https://github.com/danieloculus0-bot/BEAN/actions/runs/38104856034) (4/4 passing). The exact time series, policy vectors and claim/counterclaim/check records are in the attached `triad-longitudinal-*.json` artifacts. Data below come from the unmodified CI reports, not invented example results.

**Experimental boundary:** A, B and C are three independently initialized *synthetic* learners with an identical update rule, inputs and labelled training schedule. Roles rotate. Real code interfaces from selector PR #32 and builder PR #33 were separately checked out at their pinned commits on both OSes and passed a bounded integration test. No three autonomous model instances are currently running, and their independent identity or agency has not been established.

## Same fixed panel, accuracy %

Exactly the **same 140 questions**, no labels supplied to training. Panel SHA is unchanged for all seven evaluations.

| Iteration | A | B | C |
| ---: | ---: | ---: | ---: |
| 0, untrained | 60.00 | 85.00 | 90.71 |
| 1 | 92.86 | 92.86 | 93.57 |
| 2 | 95.00 | 94.29 | 94.29 |
| 3 | 96.43 | 96.43 | 96.43 |
| 4, source shift begins on *fresh* inputs | 96.43 | 96.43 | 95.71 |
| 5 | 91.43 | 91.43 | 91.43 |
| 6 | 91.43 | 91.43 | 91.43 |

## Fresh unseen cases every iteration, accuracy %

There are 140 new never-trained-on questions each round. The generator changes source reliability at round 4.

| Iteration | A | B | C | Peer disagreement | Unanimously wrong |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 64.29 | 83.57 | 90.71 | 47.14% | 0.71% |
| 1 | 92.86 | 89.29 | 90.00 | 5.71% | 6.43% |
| 2 | 94.29 | 94.29 | 93.57 | 1.43% | 5.00% |
| 3 | 94.29 | 94.29 | 93.57 | 2.86% | 5.00% |
| 4, shifted | 86.43 | 86.43 | 85.71 | 0.71% | **13.57%** |
| 5, shifted | 90.00 | 90.00 | 90.00 | 0.00% | 10.00% |
| 6, shifted | **93.57** | **93.57** | **93.57** | **0.00%** | 6.43% |

For comparison, the three **frozen initial policies on the same round-6 shifted panel** scored A 57.86%, B 87.14%, C 80.71%. Frozen policies saw identical observations but received no learning updates.

## What this establishes

**Demonstrated within the synthetic experiment:** Each policy's numerical weights change from verified training feedback. Initial performance differences narrow under equivalent budgets. New-case accuracy recovers after a simulated shift, outperforming each frozen counterpart in the final round. The repeated panel is never trained upon, the fresh panels are disjoint, and both platforms reproduce the same time series. Each claim includes a pro position, contra challenge, and complementary evidence test, with roles rotated across peers.

**Counterevidence and unresolved conditions:**
- **Consensus is not corroboration.** The disagreement rate collapses from 47.14% to 0%. All three can share a mistaken belief. During the first changed-source panel, 13.57% of cases were unanimously wrong.
- **Plasticity versus retention:** The fixed-panel accuracy decreases from 96.43% at round 3 to 91.43% at round 6 while the agents adapt to shifted cases. There is measurable forgetting/interference on this stable test.
- **Different starting priors do not prove independent thinking.** All three use exactly the same learning algorithm, training feedback and synthetic generator; their collapse to the same decisions may reflect a common inductive bias.
- **Not real autonomous code learning:** The live Python selector and code-candidate interfaces passed a pinned-commit integration contract, but no independent LLM instance proposed, executed and proved a generalizable code fix.

## Next falsification experiment

Preserve the original fixed panel and all results. Build genuinely **separate source generators** and independently hosted model instances with distinct observation streams. Force each to submit an independently testable alternative, a quantitative evidence-based contradiction and one new discriminating experiment; prohibit any model from grading its own proposed patch. Score paired fresh accuracy, minority-correct dissent, unanimous error, calibration, action cost, source drift, and retained skill after domain changes. Do not tune model parameters using the already-inspected Lab018 holdout.

Verdict: **SYNTHETIC_ITERATIVE_LEARNING_OBSERVED; INDEPENDENT_AGENTIC_DISTINCTION_NOT_DEMONSTRATED.** Keep Lab018 in draft research until real paths show independent, fresh, reproducible improvement.

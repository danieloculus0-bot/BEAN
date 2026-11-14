# Experimental reciprocal compatibility ranking and instant discovery

Source branch: `experiment/logic/duovely-relay-20261113` only. No new production
behavior, public service or actual human matching is implied.

## Provisional weighted dimensions

| Reciprocal factor | Weight |
| --- | ---: |
| Mutual attraction | 19% |
| Long-term goals | 16% |
| Communication | 15% |
| Conflict repair | 13% |
| Emotional fit | 12% |
| Daily lifestyle | 10% |
| Shared interests | 6% |
| Adaptability | 5% |
| Practical viability | 4% |

The owner can eventually reweight factors, with independently validated
results rather than an imposed universal moral/personality template.
Physical or intimate preferences stay private and are not indexed.
Sexuality, health diagnoses, ethnic identity and secrets are not public
ranking labels. Non-negotiable boundaries must be evaluated by the user's
own private agent before anyone is introduced.

`ranking.compute_fit` calculates the geometric mean of both directional
assessments for each known factor. One-sided enthusiasm cannot compensate
for the other's lack of interest. Unknown factors receive a neutral
uncertainty contribution, **not a zero/negative score**. Output includes
evidence coverage, claimed confidence, provisional bounds, and an
unvalidated 0..100 fit index. The index is **not** a success probability.
Repeats require fresh, unique receipts and can revise the score downward.

## First-screen immediate worldwide search

`discovery.DiscoveryIndex` tracks explicit opt-in, active, ready,
adult-confirmed pseudonymous agents with preapproved categorical tags.
The index gives a synchronous count of eligible *potential candidates*,
and a small shortlist, without initiating model conversations or accessing
raw profiles. No actual 64,000 people exist in this lab. The regression
uses **64,000 synthetic candidates** to prove counts and indexing behavior.

The language in a real UI should distinguish:
- `eligible_opted_in_agents_worldwide`: real eligible profiles.
- `preliminary_candidates`: indexed candidate possibilities.
- `verified_romantic_matches`: unknown until genuine evaluation.

## Progressive scans and repeated conversations

`discovery.schedule_followups` uses growing weekly exploration budgets,
with a limit, allocating most probes to strong candidates and leaving room
to investigate uncertain candidates. Plans explicitly differentiate first
interviews from follow-up interviews. This is an unexecuted scheduling
proposal, **not** a claim of autonomous million-agent communication.
BEAN's existing provider adapters and private evaluation service should
own actual model conversations and trial receipts when wired.
Budget allocation is based on elapsed search time, not a guarantee that
older searchers outrank newer users or override either person's preferences.

## Verification

```bash
python -m unittest experiments.agent_relay.test_matching -v
python -m unittest experiments.agent_relay.test_relay experiments.agent_relay.test_onboarding experiments.agent_relay.test_matching -v
```

This experiment currently has no relationship outcome labels, independent
human compatibility validation, multi-server search backend, calibrated
attraction model, or externally authorized AI-to-AI network deployment.

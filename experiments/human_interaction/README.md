# Lab027: Human Interaction Correction and Recovery

**Status:** deterministic baseline, **not** evidence of BEAN learning.

Motivating witnessed interaction: an assistant mistook the single-word correction "leave" (fixing "elave" in the preceding joke) for a command to end the chat. The user clarified; the assistant repaired the misunderstanding and incorporated the event into humor. This lab tests an agent's ability to use conversational context rather than simply reacting to imperative-looking words.

## Reproduce

```bash
python -m experiments.human_interaction.lab027
```

The four local fixtures cover correction, repair, humor continuity and a genuine exit instruction. Each answer earns one point for satisfying its required content and one for not emitting prohibited content. Maximum: 8. The deterministic policy is a **control**, and the fixtures are deliberately small and constructed, so a perfect score is not a generalization result.

## What real learning evidence would require

1. Capture a pre-intervention model response under identical model/version, temperature and context budget.
2. Save a scored correction as a lesson in BEAN's existing persistent, provenance-aware journal.
3. Restart the agent, compare new *unseen* conversations with no-memory, chronological-history, relevant-lesson and irrelevant-memory placebo arms.
4. Score human-rated intent accuracy, recovery quality, harmful overconfidence, unnecessary exits, humor preservation and response brevity. Use blinded evaluators and record disagreement.
5. Publish actual model identities, case IDs and hashes, complete responses, independent grades, token/time cost, and regressions.
6. No transcript retention or publication without permission. Use fictional or redacted fixtures by default.

**Critical distinction:** this lab encodes a correction behavior directly. It cannot prove BEAN learned that behavior from experience. Such a claim requires the controlled memory experiment above.

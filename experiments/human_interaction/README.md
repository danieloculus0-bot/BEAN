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

## Executable adaptation (experimental)

`adaptive.py` goes beyond the fixed scoring baseline. It selects an action from three choices (exit, correction, clarify) based on a compact context feature, accepts signed human feedback on the chosen action, updates the action value, and executes the revised policy on future turns. SQLite stores the learned values and feedback ledger across process restarts. The feature key excludes the raw conversation text.

Try the deliberate before/feedback/after/restart demonstration:

```bash
python -m experiments.human_interaction.adaptive --db lab027-demo.sqlite
python -m unittest bean.tests.test_human_interaction_lab027 -v
```

The demo uses fictional dialogue and **supplies its own positive and negative feedback** to prove that the policy changes; it is not an independent human or neural learning result. Use a fresh temporary database for the demonstration; repeated calls to the same file preserve and modify prior learned values. The policy is not yet wired into BEAN's chat interface or model-driven response generator, and this experiment does not confer any action authority. A wider deployment requires human feedback provenance, better intent features, multi-context holdouts, and matched-model ablations. Short feature patterns can overgeneralize, so monitor false corrections and reversal behavior.

**Optimization first, play second:** reward useful correction and recovery, preserve genuinely intended exits, then measure humor continuity without sacrificing intent accuracy.

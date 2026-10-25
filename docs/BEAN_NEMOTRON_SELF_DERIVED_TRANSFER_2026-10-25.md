# BEAN research: model-derived lessons on two different rule families

**Aim:** Go beyond [the first real Nemotron transfer study](https://github.com/danieloculus0-bot/BEAN/tree/experiment/bean-task-matched-transfer-20261025/research/real_reasoning/run-40206850819), which gave the model the correct procedure explicitly and evaluated two held-out examples.

## Fixed protocol

Use exactly one provider and served model for the complete paired comparison, `nvidia/nemotron-3-ultra-550b-a55b:free` on OpenRouter. Separate `OPENROUTER_API_KEY` is available only to the secret-bearing Actions job. No paid fallback, retries, execution privileges or real financial trades. **Hard request budget: 50, with provider responses and token usage written to `provider_calls.jsonl` as they arrive.**

Two independent fictional families test different operations:

- **ORCHID-7:** organize letter/digit tags into a dispatch key (ordering task).
- **HARBOR-4:** identify a gauge label from three quantities (median task).

The two families have 20 different fixed public questions in total (three development demonstrations, one development validation question, two selection questions, and four sealed held-out questions per family). The evaluator knows the answers; model requests contain only public questions and available contextual BEAN lessons.

For each family, in order:

1. Ask the actual reasoning model a cold development question. It must genuinely fail before a correction can be justified; if correct, mark inconclusive.
2. Present **only three development input/output pairs** to the *same reasoning model*, requesting it to **write one generalized lesson**. The experiment does not hand it the hidden rule in words.
3. Store the model-authored rule, the actual cold error, the correct development answer, and model response/evidence identifiers in the **existing BEAN ExperienceBank**. This is evaluator-provided feedback, not autonomous discovery of reality.
4. On a distinct fourth **development validation question**, test whether the model's lesson actually works. If not, retain the failed reflection and halt selection for that family. Only passing rules may become `retain_skill(... passed=True)`.
5. Match five arms on two development selection questions: **cold**, irrelevant **placebo**, model-authored **reflection**, validated **skill**, and **raw development examples** as instruction-candidate control. All arms use the same model; the existing BEAN selector freezes whichever wins from the scored development cases.
6. Close SQLite, open a new ExperienceBank and resolve BEAN's chosen strategy from the journal. Finally test **four new held-out questions** with frozen **cold, placebo and adaptive** arms and preserve every response, hash and score. Do not select on holdout scores.

The testing code and answers exist in the repository, but are not forwarded to the external model except for development examples and the public question being tested. The evaluator was written by the experiment author; this is **not a truly independently blinded real-world benchmark**. The model may know arithmetic and sorting already, and the conditional fictional protocol name can itself serve as a memorization cue. A 4/4 adaptive result alone does not demonstrate independent rule discovery, semantic transfer to unrelated domains, changed neural weights or profitable autonomous trading.

## What counts

A real run must have served model identity, real response IDs, complete provider call log, original SHA-chained BEAN journal, selection and holdout receipts and frozen restart evidence. Null, 429 and incomplete results are recorded as failures/inconclusive, never imputed as successes. Unit tests inject a `synthetic_fixture` only to verify exact experiment wiring; **fixture scores are not provider results**.

## Publication gate

Keep in stacked draft research PR until the two-family run is reviewed. A positive result is evidence of within-family **model-authored feedback retention and use**. Wider or independent transfer will require additional externally authored tasks with independently withheld answers, multiple random seeds or real providers, and evaluation against an equally informative raw-example baseline. No change to hosted BEAN or AIscend live execution.

# BEAN Learning Gates: Lessons Applied (2026-10-11)

**Status:** evidence-based operating criteria for research and promotion; documentation does not turn on a new learning engine. This is a living record of what the current experiments actually establish.

## What is cooking

| Stream | Evidence | Current disposition |
| --- | --- | --- |
| Persistent lessons and transfer, Lab023 | Real Ollama 0.5B model generated reflections, stored them in BEAN's SQLite journal and reopened them. Cold holdouts passed 4 checks versus 6 for retained context, but candidate omissions and unmatched served-model receipts invalidate a causal comparison. [Run 38112389946](https://github.com/danieloculus0-bot/BEAN/actions/runs/38112389946). | **INCONCLUSIVE.** Persisting memories works in the trial; transferable advantage is not established. |
| Causal memory ablation, Lab026 | Draft [PR #96](https://github.com/danieloculus0-bot/BEAN/pull/96) compares cold, chronological history, evidence-ranked lessons and irrelevant-memory placebo using the same local Ollama model; [pilot](https://github.com/danieloculus0-bot/BEAN/actions/runs/38181156634) reports protocol checks, not a replicated causal advantage. | Research only pending independent verdict and replication. |
| Model-written Core selector repair, Lab020 | Source proposal passed 14/14 development and 7/7 fresh holdout checks. Original laboratory Windows hash protocol had a failure; [PR #51](https://github.com/danieloculus0-bot/BEAN/pull/51) is the review boundary. | Candidate, not an adopted upgrade without independent full CI and merge. |
| Core autonomous self-repair | Main's scheduled [workflow](../.github/workflows/bean-autonomous-selfrepair.yml) uses real Qwen inference, source hashes, a red baseline and independent Windows/Linux acceptance. A checked run rejected an unchanged proposal and later inference failed. | Never claim a promoted self-repair without a commit and both evaluator receipts. |
| Source-trust revision, Bridge Labs003/004 | Synthetic detection improves in some changing-source settings but remembered trust underperforms recalibration in others. See [research index](experimental-research-index-2026-10.md). | Lessons may expire: verify drift, recheck and retain evidence of regressions. |

## Learned operational rules

1. **Separate memory from learning.** A stored reflection, restart success, code proposal or passing smoke test is not sufficient evidence of improvement on new tasks.
2. **Never make an invalid trial look successful.** Missing code, provider quota failures, parsing errors, hashes that do not match, absent receipts and mixed model identity produce **INCONCLUSIVE**, not zero treated as a comparable learned result.
3. **Keep a real control group.** Compare at minimum no memory, chronological history, evidence-ranked lessons and irrelevant-memory placebo. Match the actual served model, task distribution, evaluation budget and test conditions; counterbalance arm order.
4. **Only score outcomes with independent evidence.** Preserve source SHA-256, exact model identity, candidate presence, independent holdout pass counts, runtime and tokens/cost where available. Credential-bearing generation jobs do not execute model-authored source.
5. **Treat lessons as hypotheses with expiration.** Record the producing task, score, provenance, date and failure conditions. Downgrade or quarantine a lesson when independent observations contradict it or when it regresses on an updated distribution. Do not delete counterexamples.
6. **Promotion requires reproducibility.** Repeat across fresh seeds and unseen problem families, require positive effect without regressions against cold and placebo controls, and complete cross-platform CI. Document the measured uplift and cost per improvement before integrating into Core.
7. **Constrain autonomous changes.** Research findings may propose code on branches; only source-hash-bound, reviewed and independently verified changes can enter production. Record exact merged commit before calling a feature installed.
8. **Do not equate improving a wrapper with training weights.** BEAN may improve behavior through memory, policy updates and code revisions. Claims about neural weight updates require evidence of training and a changed checkpoint.

## Next experiment acceptance record

For each run, publish a machine-readable JSON/Markdown receipt with:

- base Core commit, research branch and experiment version
- model requested **and** model actually served for every attempted arm, even invalid proposals when observable
- task IDs, predeclared hidden grading rubric, random seeds, arm order and identical budget
- source SHA for each proposed candidate, or explicit `NO_CANDIDATE` and reason
- learning-journal tip/hash, successful reopen, scored evidence, and the exact lesson IDs used
- independent grader verdict per task and per operating system
- no-memory, chronological, ranked-memory and placebo performance including all regressions
- effect sizes and costs with replication intervals; do not extrapolate from a single pilot
- classification: `INCONCLUSIVE`, `NOT_DEMONSTRATED`, `POSITIVE_PILOT` or `REPLICATED_ADVANTAGE`

**Gate for changing production behavior:** do not install learning-derived strategies or silently mutate other applications based solely on a synthetic pilot. Only promote the exact independently tested implementation after comparisons, regression review and a verifiable Git commit. Keep failed hypotheses and their evidence searchable.

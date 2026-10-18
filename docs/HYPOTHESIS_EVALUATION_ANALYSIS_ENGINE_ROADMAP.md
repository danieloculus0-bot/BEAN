# BEAN Hypothesis Evaluation and Analysis Engine (HEAE)

**Status:** Proposed research roadmap, not a deployed BEAN capability  
**Originator / product direction:** Daniel Boone · 2026-10-18  
**Reference experiment:** BEAN-LP-PEMDAS-001 on the public-safe BEAN AI Bridge

## Purpose

Build a domain-aware scientific hypothesis engine that does more than accept a user hypothesis or run a benchmark. Its job is to **formulate falsifiable alternatives, design controlled experiments, evaluate measurements, quantify uncertainty and bias, and recommend what evidence to collect next**. It must retain failed and inconclusive tests as well as positive findings.

This is intended for language processing, software engineering, manufacturing, **physics**, robotics and other scientific questions. Its calculations must be reproducible; an LLM alone is not the measuring instrument.

## Core loop

1. **Register the hypothesis.** Version an explicit, falsifiable statement; identify the target effect, prediction, competing explanations, prior assumptions, study owner, and stopping rule.
2. **Check the experiment's validity.** Identify independent/dependent variables, controls, confounders, leak paths, measurement error, ground truth, blinding, and sample size. Flag tests that cannot discriminate hypotheses.
3. **Select a method.** Distinguish observational, simulated, theoretical, bench and randomized measurements. Do not call a synthetic simulation a physical experiment or a heuristic grader an LLM evaluation.
4. **Freeze the protocol.** Hash input documents, source code, ground-truth answer keys and prespecified metrics. Keep the test key unavailable to test agents.
5. **Execute within authorized scope.** Run tools, collect timing provenance and exact logs, prevent cross-agent memory sharing, and document any limits on timing or model availability.
6. **Evaluate.** Compute per-trial results, error bars, variance, effect size, confidence/credible intervals as appropriate, sensitivity to assumptions and multiple-testing correction when applicable.
7. **Challenge.** Attempt independent replication, adversarial examples, held-out trials, ablations, negative controls and alternate causal explanations. When evidence is insufficient, output **inconclusive**.
8. **Revise with provenance.** Preserve failed hypotheses; register modified hypotheses as new versions instead of quietly rewriting a result.

## Mnemonic recovery as an experimental capability

**Key research requirement:** Assessment must include **recovery from mnemonic cues after the original information is no longer accessible**, not just fact copying while it is visible.

BEAN-LP-PEMDAS-001 will compare **two isolated readers** with the same model and limits:

- **Sequential control:** Process the source in native order.
- **PEMDAS candidate:** Brief global preview using the originator's practical noun/verb entity-action anchors, then read selectively or exhaustively, deliberately retaining anchors and exact qualifiers.

Both readers receive **identical** documents, compression format, decompression privilege, processing budget, questions and scoring code. Both may use the **same generic cue prompt** after source removal; cues may also be recalled **from the agent's own saved notes**, but never synthesized from the held-out answers or newly reopened documents.

### Two-stage trial

**Stage A, unrestricted baseline:** Record preprocessing latency, time to first answer, total latency, accuracy and memory note size. A faster preprocessing phase does not automatically mean faster correct answers.

**Stage B, severe exposure limit:** Start two disconnected agent processes in parallel on the same compressed document. Revoke document access at the deadline, kill any source-reading workers, preserve only explicitly emitted bounded notes, and then ask both agents the same blinded questions without the source. Five predefined exposure conditions are run with repeated trials and balanced process order.

### Three separate outcome scores

1. **Unaided recall:** Ask questions without any cue.
2. **Mnemonic-cued recovery:** Ask with only a task-independent instruction to reconstruct *who / did what / to whom / where / when / why / exception* from already retained anchors; compare recovered details and relationships with the hidden answer key.
3. **Comprehension and calibration:** Questions requiring causal inference, temporal order, negation/exception handling, scene understanding, justified abstention and contradiction spotting. Track unsupported inference and cue-induced false memories.

Do **not** use retrieval from the original file or answer key after cutoff. Track which source evidence was actually consumed, not merely which filename appeared in a log.

### Fairness checks

- Shared CPU contention and worker scheduling can confound simultaneous latency; record monotonic timestamps per process, synchronization skew, processor load, repeated paired rounds, and reader-order swaps.
- Explicitly separate **algorithm/preprocessing latency**, **reader-exposure time**, **full task latency**, and **delayed response latency**.
- Avoid comparing agents with different context length, model weights, tool access, prompt token budgets, persistent memory or cue specificity.
- Check contamination by letting random irrelevant cues occur as negative controls.
- Include materials where the noun-verb skeleton is misleading without "not", "unless", quantities or scope.
- If a result is from deterministic document skimming, call it an **evidence recoverability surrogate**, never a model comprehension finding.

## Five-variable exposure study

Predeclare five exposure windows or a single independent variable at five levels; **do not quietly change model, document size and attention policy at once**. Use the same technical and narrative source sets across all levels, stratify scores by document type, and randomize run order. Repeat enough times to estimate jitter.

Report all trials, not just the best window. Hypotheses:

- H1: Preview-first has extra initial computational overhead.
- H2: Under restricted exposure, preview-first achieves higher post-cutoff comprehension than sequential reading.
- H3: The preview-first entity/action scaffold increases **mnemonic-cued recovery** after cutoff, without increasing false recall.
- H4: On narrative texts, purpose-adaptive preview improves scene and causal comprehension; do not treat slower immersive reading as a defect.

These are **predictions, not results**.

## Physics and engineering extension

A physics-capable evaluator must demand units, dimensional consistency, uncertainty propagation and explicit idealizations; specify initial/boundary conditions, numerical solver resolution, calibration and valid operating regimes. Compare model output against independent observations or exact analytic solutions where possible. Run conservation-law checks, convergence tests and sensitivity analyses. Always distinguish:

- theoretical result;
- numerical simulation result;
- bench/physical observation;
- inference based on assumptions.

Reject spurious precision and predictions outside the model's validated regime.

## Milestones and acceptance

- **M0:** Protocol/evidence registry and five-condition offline surrogate with transparent limitations.
- **M1:** Real matched two-agent execution and hard source-cutoff enforcement; randomized questions and mnemonic recovery metrics.
- **M2:** Preregistered power and statistical analysis, sensitivity/ablation, negative controls and blind verification.
- **M3:** Reusable scientific evaluation API with physics-focused unit, uncertainty, solver and empirical-validation adapters.
- **M4:** Measured reproducibility and predictive improvement on held-out tasks across domains.

Do not advertise BEAN as scientifically more accurate or capable of autonomous physical discovery until independent, reproducible, domain-appropriate evidence exists.

## Intellectual-property and source notices

The proposed product specification and phrasing in this file are documented for attribution to Daniel Boone, subject to applicable copyright, prior art, contributor and employment arrangements. `BEAN` public visibility does not by itself authorize code redistribution. Publishing research ideas on GitHub is **not** a patent filing or proof of exclusive ownership; evaluate any patent strategy before exposing nonpublic implementation details.

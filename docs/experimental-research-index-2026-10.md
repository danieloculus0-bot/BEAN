# BEAN Research Program — Experiments, Findings, and Reproducible Evidence

**Research window:** October 9–10, 2026  
**Status:** Published documentation on BEAN Core; experimental implementations stay on their respective branches.  
**Core:** [BEAN](https://github.com/danieloculus0-bot/BEAN) · **Research harness:** [BEAN-AI-Bridge-](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-)

> **Scope:** These are reproducible, mostly **synthetic** experiments involving BEAN's implemented attention, memory, uncertainty, evidence-audit, and reasoning components. They are **not** demonstrations of artificial general intelligence, subjective awareness, physical autonomy, real-world search-engine superiority, or production readiness. A green test suite establishes that the specified code and tests ran, not that all research hypotheses are proven.

## How to explore

1. Open an experiment's **research branch** to inspect its source, scenarios, benchmarks and tests.
2. Open its **findings** file to read the complete results, including failures, tradeoffs and limitations.
3. Open its **GitHub Actions run** to view the executed test log. Use **Artifacts** on that run for its JSON reports and test evidence *while GitHub retains them*. The reproducible source is the long-lived record; Actions artifacts may expire.
4. Keep source code from research branches separate from the stable [BEAN Core main branch](https://github.com/danieloculus0-bot/BEAN/tree/main). Links below intentionally point to particular experimental branches.

## Experiments and exact outputs

| Study | Question and noteworthy finding | Source and detailed findings | Executed evidence |
| --- | --- | --- | --- |
| **Core capability audit** (Oct 9–10) | Can the full core boot and its declared modules pass cross-platform regressions? The experimental audit identified an origin-covenant version mismatch and preference evidence that failed to mature. Narrow fixes were subsequently promoted to `main`. | [Core audit branch](https://github.com/danieloculus0-bot/BEAN/tree/experiment/bean-capability-lab-20261009) · [Audit notes](https://github.com/danieloculus0-bot/BEAN/blob/experiment/bean-capability-lab-20261009/docs/EXPERIMENTAL_CAPABILITY_AUDIT_2026-10-09.md) | [Core main: four-platform verified run](https://github.com/danieloculus0-bot/BEAN/actions/runs/38028390407) |
| **Evolution Lab 001** (Oct 9) | Can bounded mutation of an attention/verification policy improve anomaly detection? An initial selected policy **tied** its hand-tuned comparator on standard synthetic data; stronger generalization required more false probes. | [Research branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-evolution-lab-20261009) · [Protocol, results, reproduction](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-evolution-lab-20261009/experiments/evolution_lab/README.md) | [Simulation logs + JSON artifact](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/37995651207) |
| **Evidence Intelligence Lab 003** (Oct 10) | Can BEAN weigh source reliability and investigate contradictions without a fixed verification clock? In one 80-episode synthetic condition, drifting-source change recall improved from **7.14% to 78.57%** against the previous controller; other conditions regressed. Core SQLite cognition replay was exercised. | [Research branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-evidence-intelligence-20261010) · [All findings, ablations and limitations](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-evidence-intelligence-20261010/experiments/evolution_lab/LAB003_FINDINGS.md) | [52 passing tests + JSON](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38028778085) |
| **Model Revision Lab 004/004b** (Oct 10) | What happens when previously learned source trust becomes obsolete? Repeated verified surprises can trigger a recorded model revision. In six held-out synthetic environments, **30% independently sampled audit opportunities** yielded **92.80% mean change recall**, compared with **87.72%** without independent audits; *fresh-start memory still won slightly on mean task reward*. | [Research branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-model-revision-lab004-20261010) · [Full findings and comparative tables](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-model-revision-lab004-20261010/experiments/evolution_lab/LAB004_FINDINGS.md) | [68 passing tests on Linux/Windows + both reports + real-core pilot](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029372008) |
| **Confidence Search Lab 005** (Oct 10) | Can BEAN route search streams by its *own calibrated uncertainty* and rerank claims using evidence provenance rather than popularity alone? On deliberately syndicated synthetic misinformation, claim accuracy was **91.25%** versus **18.75%** for a popularity-first baseline, with **3.61** vs **6.00** pages examined. This was **not** a Google or live-browser comparison. | [Research branch and executable experiment](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-confidence-search-lab005-20261010/experiments/search_lab) · [Ranking source](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-confidence-search-lab005-20261010/experiments/search_lab/confidence_search.py) | [85 passing tests + ranking report](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029876766) |
| **Epistemic Continuity Lab 006** (Oct 10) | Must a very confident conclusion end learning? **No:** the experimental empirical-confidence model has a nonzero residual-uncertainty floor, keeps observed variation, lets verified contradictions reopen settled decisions, and explicitly links physical observations → measurements → claims → decisions. The evidence graph is **in-memory**, not production durable storage. | [Research branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-epistemic-continuity-lab006-20261010) · [Research/design record](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-epistemic-continuity-lab006-20261010/experiments/search_lab/LAB006_CONTINUOUS_LEARNING.md) | [100 passing tests on Linux/Windows + synthetic ranking output](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38030419931) |

**Experiment IDs reflect historical branch names, not a promise of sequential releases.** The original evolution work is named Lab 001; later controller comparisons also refer to Lab 002. All research branches remain referenceable regardless of whether their code is ultimately promoted.

## Findings worth preserving

### 1. Confidence is for decisions, never a ban on future evidence

A conclusion can be *settled for now* without becoming impossible to question. An empirical-confidence score bounded away from exactly 0 or 1 keeps the model updateable. This is an **experimental design choice**, not a calibrated physical probability or evidence that certainty is impossible in formal logic.

### 2. Source popularity and source independence are different

Repeated copies from one provenance origin are not independent corroboration. Lab 005 separated relevance, evidence strength, freshness, provenance and claim support, then used BEAN's estimate of search-stream reliability to allocate limited inspections. Its comparisons use simplified and partly intentionally adversarial synthetic page sets; no real search-engine superiority has been demonstrated.

### 3. Learning can make a system worse when reality changes

In Lab 003's *stuck sensor B → normal* 80-episode synthetic sequence, change detection was **91.67%** while carrying the learned source model, versus **96.67%** with fresh calibration each episode. Lab 004 examined surprise-triggered revision and independent checks as possible remedies. The best strategy changed with environment and metric; there is no universal winner yet.

### 4. Unexpected details can be retained without being over-weighted

Even binary computer decisions arise from physical implementation with noise, tolerances and deviations. Lab 006 records low-level variations but requires **explicit, defensible links** before assigning them relevance to higher abstractions. The current algorithm implements this principle in a small test graph, not as a validated instrument-calibration framework.

### 5. Falsifiability and recordkeeping outrank attractive scores

The harnesses intentionally preserve poorer-performing baselines, ablations, verification costs, false alarms, and revisions. Some experiments actually replay synthetic, verified observations into **real BEAN Core SQLite events, EpistemicGuard, Uncertainty Garden, Falsification Engine, and reasoning packets**. That is a successful integration test, not proof of autonomous understanding.

## What is actually in `main`?

The stable BEAN Core currently contains its original cognition and persistent-memory modules, plus two *narrow* repaired defects:

- [PR #10 — Core boot, incremental preference evidence, nonfinite confidence and regression CI](https://github.com/danieloculus0-bot/BEAN/pull/10)
- [PR #11 — Use the canonical origin covenant in reasoning context packets](https://github.com/danieloculus0-bot/BEAN/pull/11)
- [Core main CI, four configurations (Linux/Windows; Python 3.10/3.12)](https://github.com/danieloculus0-bot/BEAN/actions/runs/38028390407)

**The research controllers, heuristic web-ranking policy, and in-memory epistemic-continuity graph are NOT merged into BEAN Core `main`.** Publishing this document does not turn them on in production or alter other applications.

## Reproducing results

The research branch, not a screenshot, is the source of truth. For Lab 006 on Unix-like systems:

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git bean-core
git -C bean-core checkout 3cf85e63005d97ceaa7484b2d4d61efb0da3ee10

git clone -b experiment/bean-epistemic-continuity-lab006-20261010 \
  https://github.com/danieloculus0-bot/BEAN-AI-Bridge-.git bridge
cd bridge
python -m pip install pytest psutil
PYTHONPATH="$PWD/src:$PWD/../bean-core:$PWD" python -m pytest tests -q
PYTHONPATH="$PWD/src:$PWD/../bean-core:$PWD" python -m experiments.search_lab.confidence_search \
  --out lab005-search-ranking.json
```

The [Lab 004 CI workflow](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-model-revision-lab004-20261010/.github/workflows/bean-model-revision-lab004.yml) also contains Windows and Linux examples, plus commands for model revision, sparse calibration and BEAN Core replay.

## Research gates still open

- Test three-plus interacting information sources, correlated source ownership and richer than binary hypotheses.
- Introduce real browser retrieval with verifiable citations, timestamps, provenance and blinded relevance judgments; benchmark against actual search baselines.
- Independently calibrate confidence and account for selective-verification bias and environmental drift.
- Persist cross-abstraction evidence links in BEAN Core's durable storage with auditable migrations and replay, instead of only in-memory research state.
- Limit verification by expected information gain, cost and external-action policy; don't confuse *learning never closes* with *unlimited CPU, network, money or actuator activity*.
- Validate real sensors, model APIs and downstream integrations separately before claiming deployment readiness.

---

**Research policy:** preserve the exact branch, reports and negative results; distinguish a synthetic result from a real-world finding; promote code to BEAN Core `main` only through scoped review and passing CI. For questions, open an issue in [BEAN Core](https://github.com/danieloculus0-bot/BEAN/issues) and link the exact experiment and run.

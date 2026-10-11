# BEAN Lab 013 — Composite Growth Simulation

**Experimental and fully synthetic.** This is a multi-module reliability
calibration simulation, not evidence of broad independent machine intelligence.

## Objective and method

Instead of taking a single exam, a simulated BEAN system receives a sequence
of episodes across multiple domains. Each episode contains a hidden truth
(0 or 1) and reports from fictional dashboard, telemetry and independent
inspector sources. Some readings are missing, stale, contradictory or 0.

The policy only sees observations, NOT the outcome key. After each **training**
decision, a supervisor releases the correct fictional result. A bounded
posterior estimates which classes of source tend to be reliable. The policy
can consult that memory in subsequent decisions.

The independent **frozen control** uses the first available report and never
learns. Both control and adaptive policy see identical cases at held-out
evaluation. Feedback is NEVER provided during holdouts.

This experiment exercises real BEAN components:
- **MemoryStore:** isolated SQLite evidence records and retention through
  simulated close/reopen
- **EpistemicGuard:** candidate inference provenance and framing audits (no
  world-model promotion)
- **TaskEngine (Lab 011):** scheduled SQLite integrity checks and continuation
  after reinitialization
- **Entrance exam (Lab 012):** real MockLLMAdapter seven-stage baseline remains
  a separate capability axis, without any invented learning

The behavior-learning policy is small, explicit Python statistical code and
does not change the LLM or independent conceptual reasoning.

## Experimental design

| Stage | Default episodes per seed | Adaptation permitted |
| --- | ---: | --- |
| Preflight | 60 | No |
| Training | 240 | Supervised feedback AFTER each answer |
| Holdout, familiar synthetic data-generating process | 150 | No |
| Parallel holdout with injected sensor reliability drift | 150 | No |

Seeds: 11, 23, 37, 41, 53. Each paired trial uses the same held-out cases
for frozen and adaptive policies. The five seeds are repeated in both
normal and drift settings, for 2,400 training and 1,500 held-out episodes
**across both simulation settings**, plus preflights. These are repeated
synthetic fixtures, not independent field observations.

Training domains: fabrication, deliveries, cooling.
Held-out domains: energy, maintenance, inventory.
These domains SHARE source-type labels, so transfer claims are limited to
source calibration, not semantics or generalized conceptual understanding.

A drift trial secretly degrades telemetry accuracy in the second half of the
holdout. The model does not retrain during holdout; failure under drift is
intended to reveal a weakness and must not be hidden or averaged away.

## Scorecard

- **Outcome quality:** correct, incorrect, and N/A results, answer coverage,
  accuracy among answered and accuracy across all episodes
- **Utility:** +1 correct, -2 incorrect, -0.3 unknown, reported per episode
- **Growth curve:** training results in windows of 40 episodes
- **Transfer:** paired control versus calibrated policy by held-out domain
- **Robustness:** changed telemetry reliability and conflict/missing/stale cases
- **Uncertainty:** missing is unknown; a measured 0 is not missing
- **Evidence discipline:** source reference must exist and support the stated
  reading; all results remain unverified inferences
- **Continuity:** source-reliability memory survives a simulated restart
- **Runtime:** bounded periodic integrity tasks run on BEAN TaskEngine
- **Permission:** zero verified-world claim promotions and external actions
- **Separate reasoning baseline:** actual mock provider score from Lab 012

Composite scores are descriptive, not universal intelligence coefficients.
The EpistemicGuard confirms claim shape/provenance, not empirical correctness.

## Run

    python -m bean.evaluation.composite_growth
    python -m bean.evaluation.composite_growth --report /tmp/bean-growth-013.json
    python -m pytest bean/tests/test_composite_growth_lab013.py -q

Default run produces a deterministic JSON evidence report. It makes no network
requests and requires no hardware or API keys. The report includes per-seed
results, drift losses, domain breakdowns and the separate mock reasoning score.

## Gaps and next exercises

1. Read-only supervised feedback is not independent evidence acquisition.
2. General language reasoning is still the actual BEAN mock provider; source
   calibration does not teach it a new skill.
3. The simulator's report generators and reliability labels are deliberately
   public. Test fresh private hidden generators before stronger claims.
4. This memory records feedback in an isolated temporary DB; no permission is
   granted to change identity or world claims.
5. No network, real ERP events, camera, motor or robotic body runs occurred.
6. Retention verifies SQLite close/reopen only, not hardware failure or cold
   backup restoration.
7. Drift is a falsification scenario: include any negative results in reports.

Next: integrate an actual model behind Lab 012; add a strictly read-only
probe simulator; compare the same model with/without coaching, calibration,
and retained memory; test across reboot and truly unseen domains. Gate all
changes via branch review and human permission.

## Branch dependency

Lab 013 builds on draft Lab 012, which builds on draft Lab 011. Keep the
experiment unmerged until dependencies are reviewed. The separate trust/care
Lab 010 remains independent.


## Regression exposed by integration

The first composite run found that MemoryStore.init_store could swap a database
path without closing its existing thread-local SQLite connection. A later test
case could silently keep writing to the previous database. That made simulated
retention and feedback measurements invalid. Lab 013 changes init_store to
close the current thread's prior connection before constructing a new store,
and adds an explicit two-database isolation/round-trip regression.

This is a code-lifecycle fix and not evidence of improvements in BEAN's
general reasoning. Connections held in other threads are not closed here;
the host must coordinate shutdown/reinitialization of worker threads.

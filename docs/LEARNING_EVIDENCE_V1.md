# BEAN learning evidence v1

**Status:** Experimental capability on a review branch, not automatically enabled or proof of autonomous learning.

Source: [BEAN learning evidence module](../bean/evaluation/learning_evidence.py). Regression suite: [learning evidence tests](../bean/tests/test_learning_evidence.py).

## Use

Caller passes an existing authorized SQLite connection to LearningEvidenceLedger, then appends events with an event_id, claim_id, stage, source_ref, and nonempty evidence payload. The API verifies the hash chain at startup and before reads and writes. The original payload survives restart and a repeated identical event ID is idempotent, while changed content under the same ID is rejected.

Allowed stages: observation, hypothesis, experiment, reflection, change, review. Source identity remains **host asserted** and the chain requires separate external attestation for stronger integrity.

The assess_matched_trials function accepts TrialMeasurement records representing control, placebo, and treatment for the same task and replicate. It enforces equality for declared model ID/revision, source digest, protocol digest, token budget and grader reference, and unique run IDs. It produces paired scores and latency differences, never an autonomous-learning success declaration.

**This is a structural test gate, not a real agent experiment.** Even high treatment scores are labeled pilot_only or awaiting_independent_replication with causal_learning_demonstrated set to false.

## What remains outstanding

Actual independently instrumented and isolated model runs, blinded question/answer keys, severe exposure window controls, durable prompt/policy version references, objective benchmark scoring, placebo checks, externally anchored source evidence, uncertainty calibration, and integration with BEAN's current long-term memory.

This module uses no external Python packages and copied no upstream source. See [the third-party license audit](PEER_COMPONENT_REUSE_AUDIT_2026-10-18.md) and [the broader hypothesis evaluation roadmap](HYPOTHESIS_EVALUATION_ANALYSIS_ENGINE_ROADMAP.md).

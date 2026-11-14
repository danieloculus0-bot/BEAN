# OpenNARS-inspired evidence revision in native BEAN Core

November 14, 2026

## Source, license and scope
Source: [OpenNARS for Applications](https://github.com/opennars/OpenNARS-for-Applications), MIT license. Concepts studied from [Truth.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Truth.c) and [Stamp.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Stamp.c), Copyright (c) 2020 The OpenNARS authors. New Python is an original implementation of the public mathematical ideas, not a translation, vendored library or a complete NARS/ONA reasoning engine. BEAN has not adopted a new outbound license. If ONA source itself is copied later, preserve its MIT copyright and permission notices.

## Actual behavior

BEAN Core already has a permanent event ledger, world claims, a Contradiction Court and reasoning context packets. This change reuses them. `bean/cognition/evidence_revision.py` records explicit support/refute observations using the canonical `bean.memory.event_logger.log_event` API with schema `bean.nars.evidence.v1`.

For a named proposition, the reviser looks up all unsuperseded canonical observation receipts and groups them by evidence reference and source. Duplicate receipts count once; repeated submissions from one source count as one evidential vote. Source-internal disagreement or cross-source reuse of one evidence stamp is excluded and reported. Evidence with an incomplete scan yields Unknown rather than a falsely precise score.

For independent-looking **caller-identified** source groups, it computes frequency (supporting / counted) separately from confidence (count / [count + 1], an NARS-style evidential horizon). Expectation is 0.5 + confidence * (frequency - 0.5). With no observations: Unknown, frequency N/A, confidence 0, expectation 0.5. With both sides: Contested. A single-sided history remains `one_sided_unverified`, not fact.

The words "source", "independent" and "support" are host attestations. The module does **not authenticate** external evidence, establish factual truth, alter model weights, revise identity, auto-move hardware, or promote claims.

The existing runtime inbox now provides:
- `record_belief_evidence` with args `claim_key`, `polarity` (`support` or `refute`), `source_ref`, `evidence_ref`.
- `assess_belief_evidence` with `claim_key` for a read-only assessment.

The existing `build_reasoning_context` includes relevant evidence revisions for the focused world claims and retains accepted underlying event IDs in the context packet. `build_ollama_prompt` includes bounded revision details for the local small model.

## Verification

Targeted cross-platform CI runs fresh synthetic tests for no evidence, opposing observations, duplicated receipts, same-source repeats, contradictory source evidence, stamp conflict, corrected/superseded receipts, cross-session restart, incomplete scans, runtime inbox and reasoning context, and a duplicate-storm counterexample. Existing contradiction, focused-recall and reasoning regressions run alongside.

This is a deliberate small cognitive primitive with actual inference-time use, not a full NARS import or a validated measure of AGI development. The historical compressed ledger and reward scorer remain separate.

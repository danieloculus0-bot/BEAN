# BEAN Core: disjoint target validation for discovered cross-domain transfer

Source: `bean/learning/reasoning_service.py`, `NativeReasoningService.transfer_discovered_analogy`.
Regression: `bean/tests/test_discovered_transfer.py`.

## Why this change

A source-domain rule can win a small set of paired target probes and still fail
when the target changes. The previous Core transfer test compared the recovered
rule with the no-op baseline on target development probes, but required a
separate caller-managed blind benchmark to detect such failures. That remains
important. This incremental option adds a **disjoint target-validation gate**
before Core offers the resulting transfer receipt for provisional reuse.

## Contract

`transfer_discovered_analogy(..., validation_probe_ids=None)` retains the old
behavior when omitted. A caller can supply 3 to 16 distinct, fresh target
validation probe IDs, disjoint from source ancestry, prior target observations,
and the 3 to 16 development probes. The recovered source rule and comparison
against `stay_0` are unchanged.

Core measures both policies with the same resettable host reward callback.
It selects a provisional policy on development probes, then tests that frozen
choice on the disjoint validation probes. If the selected policies disagree
(including a validation tie), the returned selection becomes `None`, and
`use_tested_transfer` abstains. Validation does **not** pick a replacement
candidate. The original development winner, all individual paired rewards,
validation result, observed IDs, action choices, resource counts and failure
reason remain in the original SHA-chained ExperienceBank trial.

When 12 development and 12 validation cases require distinct actions for
the source rule and baseline, the bound is 48 host reward calls. Duplicate
actions are evaluated once per case. There are no model-provider calls,
network requests, physical actions or trading actions in this API.

## Evidence and limitations

Synthetic tests cover a stable target distribution where the source rule
continues to beat no-op, a held-out target reward reversal that forces
abstention, duplicate/ancestral probe rejection, and ledger recovery.
These are regression specifications; do not describe them as passed without
actual exact-source test output.

The target validation gate is **not** a final independent blind benchmark:
a later, completely unseen target set is still needed to estimate transfer
generalization. The host owns reward correctness and reset semantics; BEAN
does not independently authenticate either. Neither a positive transfer
receipt nor a passed test establishes AGI or subjective experience.

The separate Gauntlet draft PR #199 remains on its own experimental branch.
Its cube policy has reported 7/48 unseen-state successes and 0/10
twenty-turn successes in the cited local evidence, and it is not modified by
this Core change. See https://github.com/danieloculus0-bot/BEAN/pull/199 .

## Regression command

```sh
python -m unittest bean.tests.test_discovered_transfer -v
```

This test also belongs to the broader Core test suite. Record the exact
source commit and GitHub Actions run before reporting green CI.


## Duplicate-observation leakage check (2026-10-29)

A later Core update closes a narrower evidence-integrity gap: **fresh probe
identifiers do not guarantee fresh evidence**. With disjoint target validation
enabled, Core now fingerprints the observed numeric sensor vectors for both
development and validation. It refuses a split containing repeated sensor
states, even when the host relabels those observations with different IDs.
It also rejects states already used by earlier transfer trials in the same
target domain, regardless of their original source rule. The checks happen
before any new host reward call. The original source and target receipts
remain untouched.

Two synthetic regressions in `bean/tests/test_discovered_transfer.py` cover
same-state/different-ID leakage within a split and across persisted target
trials, including zero reward calls on rejected inputs. The existing stable
and reversed target tests still specify the positive and negative baselines.
This changes only the opt-in target-validation path; the legacy path without
validation retains its previous behavior. Equal numeric observations in
different real contexts may legitimately be distinct tasks, so this is a
conservative **sensor-state independence check**, not proof of statistical
independence or an authenticated environment. It does not detect
near-duplicates, hidden state, or falsified host observations.

Exact-head CI execution for this update must be checked separately. Do not
count committed tests as passed without runner output. The separate Gauntlet
symmetry experiment at PR #199 reported 33/118 held-out cube successes against
6/118 unchanged SpongeTD, with 0/30 twenty-turn successes, in local
synthetic evidence; no Gauntlet branch files were edited here.

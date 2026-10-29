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

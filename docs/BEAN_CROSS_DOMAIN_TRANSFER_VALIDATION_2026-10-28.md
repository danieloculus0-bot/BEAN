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


## Incomplete host-feedback receipts (2026-10-29)

A host reward callback can fail partway through a paired transfer evaluation.
Previously that exception aborted the call before a transfer trial was written,
losing the partial measured rewards and the reason for stopping. The Core
`transfer_discovered_analogy` implementation now records a **fail-closed
abstention** with `comparison_result=host_reward_failed_abstain` and
`selected=None` if a host reward raises an exception or returns a nonfinite
or nonnumeric value. This applies to both development and target validation.

The existing SHA-chained trial includes the completed paired observations,
individual successful action/reward measurements, attempted-versus-completed
reward counts, failure stage, probe, action, policy, and bounded exception
class. The raw exception message is deliberately **not** copied into the
journal. If validation fails after development succeeded, the original
development selection and completed validation pairs remain visible but
cannot authorize a policy. `use_tested_transfer` abstains for that receipt.

A failed reward is never imputed as zero, treated as a tie, or counted as a
successful paired comparison. Caller input validation (including the margin)
still rejects invalid requests. Source/target ancestry and duplicate-state
checks remain unchanged. No external provider, device, or trade is invoked.

Three synthetic regressions exercise interrupted development, interrupted
validation after a completed development phase, nonfinite rewards, durable
restart recovery, and refusal to reuse an incomplete transfer. They are
test **specifications** until an exact-source runner confirms execution.

The Gauntlet branch remains untouched. Exact-head Gauntlet run
[40822971069](https://github.com/danieloculus0-bot/BEAN/actions/runs/40822971069)
at `b7624e182e412288089de3ca7963e1aeb561fd9b` finished with eight
successful jobs and uploaded case-level artifacts. That verifies those
synthetic experimental regressions, not deployment or general intelligence.


## Active-hypothesis revision sensor ancestry (2026-10-29)

Core's existing `discover_analogy` and `revise_discovered_analogy`
previously checked that revision **probe IDs** were unseen. That was not
enough: a host could relabel an old numeric observation as a fresh case,
including an observation BEAN had seen but never spent a reward call on.
A revision could then earn undeserved evidence credit.

The active-hypothesis result now retains a stable SHA-256 fingerprint of
**every** observed numeric sensor vector, including the full development
pool and any validation pool. The revision checks these fingerprints across
the immutable parent/ancestor receipts and against all observations in its
own new pool. Repeated values under different IDs fail before a single
new host reward call. The original parent receipts remain append-only.

Historical receipts created before complete fingerprints existed cannot
reconstruct unrecorded observations. The revision compares their retained
rewarded and validation observations, and explicitly records
`ancestry_sensor_coverage=legacy_rewarded_sensor_states_only` rather than
claiming complete independence. New-format ancestry records
`all_observed_sensor_states`. Equal vectors in different hidden contexts
may represent different tasks, and unequal vectors can still be correlated:
this is an exact-state anti-recycling check, **not** statistical independence,
real-world OOD performance, or authenticated host evidence.

Three synthetic regression tests in
`bean/tests/test_active_hypothesis.py` cover restart persistence,
relabelled **unrewarded** ancestor observations, repeated fresh observations,
relabelled validation observations, and the unchanged successful fresh
revision path. They are committed specifications, not claimed passing
until exact-source runner output is inspected.

The separate Gauntlet PR #199 was inspected at `01cc9c608187`.
Its new validation-directed cube curriculum remains experimental and its
exact-head CI was not confirmed by the available run lookup. Prior verified
Gauntlet learned-value rollout run 40841033958 passed eight jobs, and
mainline rollout run 40841426306 passed four jobs; neither proves this new
Core revision change passed. Gauntlet files were not modified.

Targeted command:

```sh
python -m unittest bean.tests.test_active_hypothesis -v
```


## Development-only target anti-recycling (2026-10-29)

The earlier exact-state check ran only when callers supplied optional
target validation cases. A caller using the default development-only
transfer path could therefore relabel duplicate numeric sensor states,
or recycle states from a previous target-domain trial, and earn apparent
new transfer evidence. The same existing fingerprint check now runs
**before host reward calls on both paths**, preserving the validation
option and its stricter disjoint-split requirements.

Two new synthetic regressions require zero reward calls and zero new
trial receipts for relabelled duplicates within a development pool and
for a repeated state from a prior persisted target trial. The original
positive and negative transfer controls remain unchanged. The targeted
GitHub workflow now includes the discovered-transfer suite; its exact
source run must be checked before reporting tests as passed.

This is exact numeric-state anti-recycling, not proof of independent
sampling, unseen hidden state, out-of-distribution generalization,
consciousness or AGI. Existing SHA-chained receipts are not rewritten.
Gauntlet PR #199 and its experiment branch were not modified.

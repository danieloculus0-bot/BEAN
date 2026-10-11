# Lab 022: BEAN repairs its own failed code-repair pipeline

**Question:** Can BEAN inspect its own rejected model-edit attempts, identify an improvement to its Python source-author loop, author a novel source patch, and independently validate that change without a human supplying the replacement?

The live Core→Bridge trial [run 38108896676](https://github.com/danieloculus0-bot/BEAN/actions/runs/38108896676) made two real OpenRouter free requests and produced **no accepted code candidate**. The latest response was recorded as `ValueError: empty or oversized edit plan` from `cohere/north-mini-code:free`. This is a genuine failure to recover from an unusable model response, not a successful code repair.

Lab 022 grants BEAN a strictly bounded **self-repair research sandbox**. The model receives its own original `bean/evaluation/bridge_peer_live_author.py` source at immutable Core SHA `3aaec786ad8b9d5685573c62bb4fc39119c0d65b` plus the sanitized failing-run evidence. It is asked to diagnose and improve the failed source-author. **No human-authored patch, implementation recipe, or holdout test source is passed in the model prompt.**

## Independent acceptance

- The baseline module is independently checked against a separate holdout file. That oracle checks that a failed model response leads to *materially different, still useful* generation strategy on retry, rather than the former almost identical oversized prompt. The original pinned baseline is expected to fail this oracle.
- A model-written source patch is not enough. It must preserve existing function contracts, reject untrusted/invalid code and arguments, avoid paid provider fallback, and still honestly fail closed when the provider returns no usable source.
- The proposed source is AST-parsed, bounded to at most 100 source changes, and SHA256-addressed, without execution in the key-bearing author job.
- Different Linux and Windows GitHub Actions jobs with no model key run the complete Core regression suite plus holdout. They restore the baseline and emit independent verdict receipts. **Both OSes must accept the exact same hash**.
- Only a passing proposal is pushed into a new review branch and offered as a PR. It cannot auto-merge to production main.
- The model is strictly routed to `openrouter/free`, with up to three calls per run. Provider access, quota, model quality and CI readiness may prevent success; failed attempts produce truthful receipts.

## Peer review and next step

The Bridge's meta-invariant hunter remains independently active ([Bridge PR #24](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/24)), and Core's development-engine work remains available ([Core Lab019 PR #37](https://github.com/danieloculus0-bot/BEAN/pull/37)). Engineering peers can challenge BEAN's self-repair PR from the shared [peer thread](https://github.com/danieloculus0-bot/BEAN/pull/33). This test is about improving *BEAN's own code*, not merely a fixed-template repair of an artificial target.

**Evidence rule:** A passing infrastructure/test run means the laboratory is operational, not that a real self-repair has succeeded. The code generation and independent holdout runs are the required proof. Do not raise an autonomy score based on having this workflow alone.

## Unattended verified repair pipeline (October 11, 2026)

The scheduled workflow now attempts an actual, bounded upgrade to BEAN Core's
own model-code author when the witnessed defect is still present. It can use
OpenRouter free inference, then local Qwen2.5-Coder 1.5B when free API
inference is rate-limited. A model must return real source edits. The author
records every failure and does not execute generated source near credentials.

Independent Linux and Windows jobs reproduce the red baseline, apply the exact
candidate in separate unprivileged runners, run the hidden acceptance and Core
regressions, then preserve hash-matched verdicts. The source cannot modify
imports, provider globals or unrelated functions.

If both platforms pass, a separate write-capable job attempts a non-force
fast-forward into main automatically. Protected branches or source drift
instead retain a review branch and report the blocker. This is an actual
automatic source upgrade only if the final branch update succeeds, not merely
an experiment or an automatically opened PR.

The objective remains limited to this specific independently witnessed defect.
Future problems require independent acceptance tests; no arbitrary self-edit
may bypass them. After the source changes, stale benchmark retries are skipped.

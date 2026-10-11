# BEAN vs Aider — Round 2: optimize the exact Round 1 fixes

[Round 1](https://github.com/danieloculus0-bot/BEAN/actions/runs/38110050070) ended **2–2, 16/16–16/16**. BEAN and unmodified Aider solved the same ledger and permission-graph programming defects using the same named free model. Aider was faster in the authoring stage (roughly 20 seconds total versus BEAN’s 33 seconds), but **we did not measure the execution speed of the generated algorithms**.

This new round tests **code optimization**, not merely successful generation speed. It downloads the untouched source files that the actual two agents wrote in Round 1 from the existing immutable artifact `bean-vs-aider-authors-38110050070`. It does not substitute any human reference implementation or mutate Round 1 source.

## Assignment

Both agents receive the same optimization objective and their own previously passing source from Round 1, for each of the two original problems. Their goal is to improve execution speed without losing correctness. Upstream `aider-chat==0.86.2` and BEAN's existing model-backed source-edit agent again request the same explicit OpenRouter model `nvidia/nemotron-3-super-120b-a12b:free`. Each optimization occurs in an independent workspace. This is a comparison of optimization capability on the **same tasks**, but each agent starts from its own correct source (not literally identical code). BEAN may make at most two edit-plan requests; Aider's internal request count is not audited. No hidden tests are sent to either.

## New independent judge

Linux **and** Windows CI independently retrieve the exact Round 1 artifacts and both Round 2 submitted sources. Neither verifier has the model API secret. The judge checks:

- The exact Round 1 source artifact, author receipt and SHA256 match the frozen original task manifest and original requested model.
- The **same original 8 held-out functional tests for each task** still pass after optimization.
- Additional, model-hidden large stress workloads reproduce revision replacement/order independence and timezone eligibility for the ledger, and cyclic/transitive deny-overrides semantics and non-mutating inputs for the permission graph.
- Repeated execution on the same runner, using median elapsed nanoseconds over nine trials, for both baseline and optimized variants. For each agent/case, the reported ratio is **baseline median ÷ optimized median**. A result at or below 1.0 is slower or unchanged.
- Missing candidate, failed correctness, failing stress, CLI launch failure or model error never counts as a successful optimization. CI runtime is inherently noisy; changes smaller than roughly 5% are not promoted as meaningful evidence.

## Scoring and limitations

Correctness remains a gate. If both agents submit valid optimization candidates for both tasks, the pilot compares their arithmetic mean of relative speedups; it claims an advantage only when one is meaningfully larger, **and actually exceeds 5% speedup**. If neither improves materially, the outcome is `NO_MEANINGFUL_OPTIMIZATION`. If one or both fail to produce a valid optimization the result is `INCONCLUSIVE_OR_INCOMPLETE`, not an artificial BEAN or Aider win.

Each case report includes individual baseline/optimized medians and trial samples, SHA256 source/artifact hashes, original and new test results, and stress validation. Linux and Windows reports are published separately, because computer speed is not identical across runners. Results from both platforms should agree in direction before claiming broad evidence of optimization.

This **does not** establish that BEAN outperforms Aider on general coding tasks, or that either is better than a commercial coding agent; this is a two-task reproducible engineering pilot. Model call budgets and provider internals are not exactly equal. A future preregistered larger benchmark is required to establish generality.

## Offline checks

```bash
python -m unittest bean.tests.test_agent_arena_optimization -v
```

The live run is in [bean-vs-aider-optimize.yml](../../.github/workflows/bean-vs-aider-optimize.yml). It starts after all Linux/Windows preflight checks pass on a reviewed PR merged to `main`, or by manual workflow dispatch.

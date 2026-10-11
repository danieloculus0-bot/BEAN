# BEAN autonomous engineering: recovery and reproducible optimization evidence

This increment targets **two measured weaknesses** from [BEAN vs Aider Round 2](https://github.com/danieloculus0-bot/BEAN/actions/runs/38110686371). Its source of truth is the actual immutable GitHub Actions author archive `bean-vs-aider-optimization-authors-38110686371`.

## 1. BEAN's model-format recovery

The ledger optimizer's **two real model responses contained no usable edit text**. BEAN previously repeated essentially the same JSON source-edit request, then submitted no code. We are fixing the *agent framework*, not writing the ledger optimization by hand.

- First attempt remains BEAN's original model-authored JSON `find`/`replace` edit plan.
- **Only after a rejected proposal**, BEAN changes strategy: it requests an entire model-written Python module with a larger bounded output budget. It is still the **same free model**, same source/task requirements, and at most two requests.
- The host rejects null, prose, malformed, unchanged and oversized code; preserves the task's public function name and call signature; checks Python AST syntax and the original 100-changed-line limit; then hands candidates to independent hidden functional/stress tests. A model's code is never used to modify the hidden tests.
- Receipts identify whether a candidate came from `json_edits` or `whole_python`, and whether the provider supplied nonempty content. No fixed source rewrite or previously solved sample is supplied to the model. If no valid output appears, BEAN must report failure rather than fabricate code.
- New offline protocol tests cover true model-authored full-module recovery, malformed code and source/API preservation, and hidden-test exclusion.

This **does not prove** the provider will start returning usable text; the live new attempt is the required evidence.

## 2. Paired optimization replay

The initial Round 2 benchmark reported a platform reversal: BEAN's permission-graph edit slowed Linux but improved Windows. Testing baseline and candidate in separate Python processes risks warm-up and scheduler effects. The new independent replay:

1. Retrieves the **exact previously generated original Round 1 sources**, source digests and original 8 hidden tests per task.
2. Retrieves the **exact model-written Round 2 optimization attempts** and receipts, rather than asking the model to generate or hand-adjust them again.
3. Creates an independent, credential-free Python process containing **both** original and candidate implementations, with the same deterministic large synthetic workloads.
4. Confirms both implementations agree, reject incorrect graphs/ledgers and do not mutate caller data.
5. Alternates original/candidate evaluation order across **12 matched timing pairs**, using identical datasets in one interpreter and reporting paired median speedup and 12 individual ratios.
6. Reports `FASTER_REPRODUCIBLE` only for median >1.05× and at least **9 of 12** pairs exceeding 1.05×; similarly for slowdown. Otherwise it reports `NO_CLEAR_CHANGE`. Both Linux and Windows run independently and both results should agree before considering an optimization stable.
7. Never assigns a BEAN win just because there was **no candidate** for the ledger. No previous scoreboard is changed or retroactively rescored.

This is stronger measurement evidence, but still not a controlled hardware performance study. Results depend on CPU architecture, Python/runtime version, co-tenancy and scenario selection; a larger cross-project benchmark is needed for general conclusions.

## Controls and peer collaboration

- Models and Aider both receive the same task text; the judge code is not embedded in either model prompt.
- Source artifact provenance is checked against immutable Round 1 and Round 2 GitHub Actions run IDs.
- Provider and GitHub tokens are removed from every benchmark subprocess.
- CI preflights on Linux and Windows before a full replay runs on `main`.
- The existing [Core peer ledger](https://github.com/danieloculus0-bot/BEAN/pull/33) receives the actual hashes, model failures and OS-specific measurements so other developers can critique rather than duplicate the change.

**Success rule:** install the protocol, run an actual model-backed optimization retry, and independently demonstrate correct and materially faster code. A green harness alone cannot raise a BEAN intelligence/readiness score.

Local protocol checks (no model key required):

```bash
python -m unittest bean.tests.test_agent_arena_protocol bean.tests.test_agent_arena_adaptive -v
python -m unittest bean.tests.test_agent_arena_paired_replay -v
```

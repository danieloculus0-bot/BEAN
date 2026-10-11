# BEAN Lab 019: Actual autonomous source writing and persistent iterative growth

BEAN can now **write actual Python replacement code, try multiple alternatives, run trusted tests, record all failures, and resume the same investigation**. This is a research capability that reuses the already proven Bridge autonomous-improvement pattern; it is not another fake three-learner intelligence score.

## What BEAN actually does

1. Read a designated Python source file and an explicitly stated, reproducible defect.
2. Establish a baseline by running the fixed, evaluator-owned unittest suite before proposing a change.
3. Generate a new complete source candidate through either:
   - **ASTBruteForce** (model-free deterministic control): systematically alters numeric source syntax in Python AST. It writes genuine new files. This is a limited search strategy, not novel LLM-authored programming.
   - **Ollama** (optional): call a locally hosted model's generate API to write a *complete source module*, using objective, original source and prior rejected attempts. No test source is in the prompt.
   - **OpenRouter** (optional): use the named hosted language model and a caller-controlled API key in environment, with the same source-plus-history contract. The key is never written to a journal or passed to the test process.
4. For every syntactically valid candidate, write a SHA-addressed Python source file into `output/candidates/<objective>/<SHA>.py`, then copy it into a temporary test project and run evaluator tests in a new Python process. The code really changes and executes **only in that disposable test project**.
5. Retain each attempt (successful, rejected, invalid, test logs, source digest and locked test digest) in an append-only SQLite chain. On restart, verify continuity, recover all failures, and continue the next iteration. Previously validated evidence is not discarded.
6. Promote only a successful candidate to `output/validated/<source-path>`. The working project's original source remains unchanged until a separate research-branch write step.
7. On manual GitHub Actions workflow dispatch, a **different job** can copy the verified bytes to a **new Git branch** named `bean/selfdevelop-<run>`, commit, push and attempt to open a PR **against the experimental Lab 019 branch, never main**. A read-only generation job runs first; GitHub write permission appears only in the later upload job. PR creation may be blocked by repository settings, in which case the generated branch and review link are recorded.

## Actual initial result

The seed fixture intentionally clips values to 101 instead of the required range 0–100. An evaluator-owned 7-test suite includes 101, 1000, negatives, zero, valid values and 100.5.

The model-free AST search tests several distinct changed Python source files. The first independent demonstration found a true repair after **7 candidates (6 unsuccessful, 1 successful)**: change `min(score, 101)` to `min(score, 100)`. Baseline: **3 failures / 7 cases**. Accepted patch: **7 passing / 7 cases**. The original version was not overwritten, and the successful patched source was saved separately. Replay tests verify exactly 7 attempts, new candidate hash, persistence, resumption, tampering detection and absence of evaluator test leakage.

This is **proof of source-writing, bounded search and historical learning mechanics**, not proof a neural model autonomously learned how to code. Ollama/OpenRouter adapters are functional API integrations with mocked contract tests; **no actual provider call has been made as part of the CI proof**.

## Local invocation

Use an isolated, disposable credential-free development VM or container. From BEAN root:

    python -m bean.optimization.autodev \
      --project experiments/autodev/seed_project \
      --target bean/skills/clip_score.py \
      --task "Repair score clipping so values never exceed 100 or fall below zero" \
      --journal ./private/bean-growth-history.sqlite \
      --output ./private/bean-growth-attempts \
      --provider ast --attempts 25

To use an actual local language model, replace `--provider ast` with `--provider ollama --model qwen2.5-coder:7b` with the model running. For hosted inference, use `--provider openrouter --model <permitted model>` and set `OPENROUTER_API_KEY` on the isolated generator host.

Run `python -m pytest bean/tests/test_autodev_lab019.py -q` to verify the engine itself.

The journal path should be a stable, private directory across restarts. GitHub CI uploads its run-specific SQLite journal and JSON receipts as artifacts. **CI artifacts alone are not a live shared long-term memory service**; future GitHub runs must explicitly restore a journal or integrate a durable authorized state store before claiming continuous cross-run learning.

## Autonomy scopes and limitations

- BEAN can genuinely author or mutate code, replace a test candidate file, execute the fixed unit tests and keep evidence without asking which of the predefined source patches to run.
- The AST search is constrained by its mutation operator set; a configured model may propose arbitrary Python module text but its competence and safety must be independently evaluated.
- A syntax check and 7 green fixture tests cannot establish real-world correctness. The independent test suite may miss regressions. Tested input is synthetic.
- **Executing model-generated Python is not secured by copying it to a temporary directory.** Use a separately isolated low-privilege CI/VM container with no network write credentials or secrets; the test subprocess environment is trimmed but that alone is not an OS security boundary.
- The GitHub generated-branch writer has an explicit one-file staging allowlist in an isolated job. It cannot self-approve a production merge. This is consistent with the already-working Bridge autonomous workflow.
- Future upgrades: long-lived shared run history across CI dispatches, parallel candidate execution in separate workers, independent sealed holdouts, differential coverage tests, model-provider calibration, new objectives with genuine novelty, and robust rollback under failed real-world validation.
- The Core selector in merged PR #32, the builder/peer dialogue in draft PR #33, and triad falsifier in draft PR #35 are complementary, not replaced. Candidate selection, source authoring, and independent opposition can all consume the same evidence receipts without sharing privileged write access.

**Promotion verdict:** research milestone for actual code writing and isolated testing. Do not confuse this with verified general recursive self-improvement, autonomous intelligence, or permission to deploy arbitrary model code.

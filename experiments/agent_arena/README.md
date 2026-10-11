# BEAN vs Aider — Engineering Cage Match, Pilot 01

**Opponent:** [Aider](https://aider.chat/), unmodified upstream `aider-chat==0.86.2`. Aider is an established terminal AI coding agent with its own public, multi-language code-editing leaderboard. We are *not* comparing BEAN to a fictional, deliberately weakened dummy opponent.

**Question:** Can BEAN's own model-authoring and revision logic outperform Aider's genuine code-editing agent on the same unfamiliar engineering problems?

## Exact match rules

Both competitors receive exactly the same original `candidate.py` and plain-English requirements on two neutral, synthetic problems:

1. **Ledger revisions:** deduplicate and replace event revisions rather than double-count, filter by absolute cutoff instant, and preserve input-order independence.
2. **Permission graph:** nested groups, deny-overrides-grant semantics, cycles and branch-order independence.

Original modules are deliberately defective, and eight independent tests per task verify the specifications. The preflight job proves each baseline actually fails. The test file strings are bundled in the evaluation harness but **never sent to either model**. Aider only sees the source copied into a fresh temporary folder containing no test suite. BEAN receives the same source and task prompt; it uses BEAN Core's existing `bridge_peer_live_author.parse_plan/apply_edits` implementation for autonomous exact-source edits. Neither author is given human-written patches. They have no functional test feedback during generation.

Both request the SAME **explicit** free OpenRouter model: `nvidia/nemotron-3-super-120b-a12b:free`; it is not a contest between different commercial models. Upstream Aider is invoked once in scripted, headless mode with its whole-file editor enabled. BEAN may make up to two model requests, with its own rejected-edit feedback. We preserve actual BEAN provider responses and any token usage reported, Aider exit code and timing, and all final candidate SHA256 hashes. Aider may perform internal edit retries, so precise LLM call-count parity is **not established**; record that limitation. An Aider CLI startup failure or missing model-provider credentials makes the verdict *inconclusive*, not a free BEAN victory.

The author stage never runs generated code. A **separate GitHub Actions judge without any model or GitHub write credentials** executes every candidate with the same withheld tests and original-source red baseline. Scores are deterministic: fully solved tasks first, then number of passing hidden tests. No test cases are selected after viewing model performance.

Evidence includes original source and hidden oracle hashes, agent receipts, candidate hashes, success/failure counts, runtimes, requested model and an aggregate SHA256 verdict.

## Grading

- `BEAN_WIN`: BEAN solves more tasks, or an equal number and more independent hidden tests.
- `AIDER_WIN`: Aider achieves the inverse.
- `TIE`: identical task and hidden-test scores under a viable test environment.
- `INCONCLUSIVE`: provider/token access failure, invalid baseline, missing opponent/tool or incompatible setup.

A win on **two synthetic problems** demonstrates only pilot competitiveness under these exact conditions. It does **not** show BEAN generally beats Aider, commercial agent suites, Codex, SWE-bench, enterprise AI, or AGI. Repeated pre-registered tasks, cross-language/codebase benchmarks, price/latency accounting, controlled model call budgets, and multiple seeds would be needed before a general claim.

## Reproduce

Core repository, Python 3.11 (no key required):

```bash
python -m unittest bean.tests.test_agent_arena_protocol -v
```

The official live run is [.github/workflows/bean-vs-aider-arena.yml](../../.github/workflows/bean-vs-aider-arena.yml). It requires the already-enabled Core `OPENROUTER_API_KEY` Actions secret. It installs upstream Aider 0.86.2 and performs a paired model-backed author stage, then a separate independent grader stage.

**Transparency:** This is a new harness and match, not an independently established victory until the GitHub Actions live run produces a completed verdict. Existing BEAN and Bridge code are not modified by the pilot. No customer, workplace or personal data are involved.

## Escalation if BEAN wins

The next match should add third-party, pre-registered repository defects and hidden tests, equalize actual model request/token/time budgets, and include an additional established coding agent (for example OpenHands) under a reliable supported model setup. **No editing the challenge after seeing results.** Gradually increase difficulty until the result means something.

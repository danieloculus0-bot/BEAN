# BEAN Lab024 — Iterative Specialist Coding Duel

Status: experimental, not approved for main.

## Aim
Beat a real, purpose-built coding agent on genuine source repair tasks
through *better feedback-driven development*, not by counting an offline,
crashed, invalid or unavailable opponent as a win.

Opponent: unmodified upstream Aider 0.86.2 CLI with Ollama chat backend.
BEAN: real BEAN source-edit and AST gate, with three feedback-driven
attempts, persistence via the actual BEAN SQLite hash-chained Journal.
Both: same preinstalled qwen2.5-coder:1.5b Ollama service and same public
Python task specs, both allowed three **editing rounds per task**.
Aider might spend more than one model request inside a round; exact
inference-token budgets are NOT guaranteed equal.

Tasks: immutable existing agent-arena as-of ledger replay and transitive
permission graph. Initial buggy code deliberately fails independent tests.
All candidates are original outputs from the model or unchanged Aider CLI,
never reference answers or hard-coded target functions.

Each agent gets a separate isolated copy. Development feedback is limited
to total number of tests passed; no inputs, assertions, stack traces or
full evaluation transcript are passed back. Each actual generated candidate
is tested only in Docker with no network, read-only file mounts, no
privileges, limited CPU/memory/PIDs, no GitHub or inference credentials.
BEAN records SHA256 digests and aggregate feedback in SQLite. Each agent
selects its own best development-scoring attempt before final evaluation.
A separate credential-free Linux + Windows job checks every receipt
and judges those SHA256-selected candidates on the existing hidden suites.
Hidden tests are NEVER used to pick the best candidate, and no candidate
runs in a host process with access to Ollama or OpenRouter credentials.

**Three edit rounds != model-weight training.** This tests iterative
agent adaptation through feedback and episodic memory, not autonomous AGI.
Two synthetic tasks do not establish general superiority. Some development
checks resemble public spec behavior, so holdout sets are not genuinely
novel distributions. If Aider fails to start, cannot connect to Ollama,
fails to submit a candidate, or provider identity cannot be verified,
the verdict is **INCONCLUSIVE**. A failure is never reclassified as a win.

## Reproduction
GitHub Actions:
- Normal pushes to experiment/bean-vs-aider-iterative-lab024-20261011
  run offline mocked framework regression on Ubuntu and Windows.
- An **explicit** commit containing [lab024-live] triggers Aider installation,
  Ollama model download and the real bounded 3-round match.
- Workflow: .github/workflows/bean-lab024-specialist-duel.yml
- Candidates, receipts and BEAN journal are separate uploaded artifacts.
- Independent withheld scorecards exist only in the judge's run artifacts.
- No cloud API key, GitHub secret or paid inference is used.

Local reproduction needs Python, Docker, Ollama and aider-chat==0.86.2:

    ollama pull qwen2.5-coder:1.5b
    python -m experiments.agent_arena.local_duel_lab024 author --out D:\BEAN\lab024-run
    python -m experiments.agent_arena.local_duel_lab024 judge --out D:\BEAN\lab024-run

The judge should be executed separately from authoring for credible evidence.
For this user's small Windows system drive, Ollama model storage is
D:\Ollama\models via the persisted OLLAMA_MODELS environment variable.
The hosted CI job has a separate disposable Ollama service, independent
of their PC and unaffected by free OpenRouter 429 limits.

Do not publish generated candidates to production/main or present a
synthetic-mock test as evidence of BEAN coding ability.

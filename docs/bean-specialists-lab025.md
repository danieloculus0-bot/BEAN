# BEAN Lab025 — Five Specialist Tournament

Research status: NOT merged to main. No superiority claims without an actual
independent, model-backed, comparable result. This extends Labs023 and 024,
especially their failed-source lessons, without modifying unrelated branches.

## Engineered tasks and controls

| Opponent | Domain appropriate to agent | Public objective | Withheld tests |
| --- | --- | --- | --- |
| OpenCode | API / repository compatibility | preserve URL-route matching across query/fragment/path normalization | 8 |
| Goose | manufacturing workflow | calculate objective OTD and RMA totals from synthetic JobBoss-like export records | 8 |
| OpenHands | autonomous fault recovery | recover highest valid checkpoint despite duplicates and crashed writes | 8 |
| Continue | behavior-preserving refactor | stable linear-time deduplication with complex record values | 8 |
| Cline | security / IDE regression | transitive deny-overrides-grant access-control rules | 8 |

Each opponent receives its native real CLI and the same local
qwen2.5-coder:1.5b Ollama coding model as BEAN. Each gets three
edits with aggregate DEVELOPMENT feedback, and each works on a separate
scratch copy of candidate.py. BEAN uses the real source AST/diff gate,
its Ollama coding backend, and its append-only SQLite hash-chained
Journal to retain its mistakes and measured feedback. The best source
is chosen only by independent development-test scores, before seeing
the hidden final suite. The author never receives the withheld inputs
or expected outputs. No production data are used.

All proposed code is executed exclusively in disposable networkless,
read-only Docker containers with no credentials, capped memory, CPU,
and processes. A separate GitHub Actions job retrieves SHA-attested
candidate files and runs the independent final tests. Missing agent
installation, unavailable inference, missing source, invalid receipts,
or missing model capability all produce INCONCLUSIVE, never a win.
All raw candidate artifacts and scores are retained with a 21-day
retention period.

The current model has limited capability; OpenCode's documented
recommended 64k context window may exceed efficient processing of
the 1.5B model. We set the same 65536 context configuration for
both arms, but comparable use of actual context/inference tokens
cannot be assumed across agent frameworks. A full-sized model is
a later stronger tier, and may not fit ordinary free runners.

## Running the real matches

Workflow: .github/workflows/bean-five-specialists-lab025.yml.

Push a commit containing [lab025-live] to explicitly enable five
live model-based matrix jobs. Ordinary pushes run only Linux/Windows
mock contract, invariants and source tamper preflights.
Each separate real author job downloads its own local Ollama instance
on temporary GitHub runner; no OpenRouter credits and no dependency
on the user's computer. The specialist's actual executable is
installed from the upstream provider, and installation failure is
recorded as an invalid/inconclusive contest.

GitHub Action match outputs:
- lab025-{agent}-authors : original source bytes, three BEAN and
  opponent candidates, aggregate dev scores, SHA256 journal.
- lab025-{agent}-independent-verdict : hidden score and
  BEAN_WIN, {AGENT}_WIN, TIE, or INCONCLUSIVE status.

No automatic merges to main; the user's Windows install and
D:\Ollama\models do not change. Only research branch code changes.

## Improvement lanes

- BEAN core: source parsing, retries, repair validity and honest no-candidate reporting.
- Agent infrastructure: native CLI integration and comparable local inference identity.
- Validation: Docker isolation, precommitted held-out tests, cross-platform preflights and receipts.
- Results analysis: learn from genuine failures without feeding withheld data into later attempts.

These are engineering workstreams, not claims that independent people
or AI agents have accepted assignments or performed changes.
Existing experiment/ and feat/ branches remain untouched; integrate
only with separately reviewed evidence.

## Limitations

These five deliberately small synthetic challenges are diagnostic,
not representative industry benchmarks. One task per agent cannot
establish general agent superiority. A CLI may make several internal
model requests per "round", so request and token budgets are not
necessarily matched. A headless CLI may require external login or
lack support for a 1.5B tool-calling model. Such situations must
show INCONCLUSIVE and be fixed separately before a fair victory claim.
No model weights are trained by these iterative trials.

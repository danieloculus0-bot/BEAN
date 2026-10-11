# BEAN Core → Bridge: blind, model-authored engineering trial

This experiment bridges two previously separate verified capabilities:

- Core has actually obtained a model-authored Python fix through OpenRouter's zero-cost free route, then passed 7 independent tests ([Core run 38108153901](https://github.com/danieloculus0-bot/BEAN/actions/runs/38108153901) and [run 38108215455](https://github.com/danieloculus0-bot/BEAN/actions/runs/38108215455)).
- Bridge already detects real reporting-invariant failures on synthetic inputs and preserves reproducible metadata. The Bridge has a sealed Midnight RMA Paradox oracle and a cross-platform candidate verifier.

The goal is a much harder, genuinely cross-project proof: BEAN Core's working model access **authors a novel source change** to the Bridge's actual reporting module, and independent Bridge tests determine whether the repair works. The model does not see the evaluator-owned test code or the 180-case metamorphic holdouts.

## Pinning and experiment boundaries

- Bridge source is pinned at commit `d06315bf05cae24131b19f3ce17b57d2d0b4351a`.
- The independent failing oracle is pinned at `75b12233c243b61c61b2f9b205951cb8ae45f4b7`.
- The author sees the Bridge Python source and a plain-language defect description, **not** the oracle file contents, test errors or hidden holdout cases.
- A real OpenRouter `openrouter/free` LLM creates a JSON list of arbitrary exact source find/replace operations. There is **no hard-coded repair template**. The author checks unique anchors, changed-line budget, AST syntax and SHA256, but **never executes the model output**.
- One successful candidate is recorded in the Bridge's accepted `bean.novel-repair.v1` proposal format, including original commit SHA, oracle digest, selected provider and exact proposed replacement digest. Zero, one, or two free requests may be made. Failed attempts do not generate a fabricated patch.
- Separate Linux and Windows runner jobs, without model credentials or GitHub write scope, run the existing Bridge verifier: an independently failing red baseline, all ordinary Bridge tests, and the untouched sealed Midnight RMA oracle. They then run the candidate against 60 fixed synthetic metamorphic trials and 120 additional fresh trials seeded by run ID with a strict no-finding acceptance gate.
- On failure, retain status and result artifacts. This workflow **never merges, pushes a fix or executes generated code in the secret-bearing author job**. A manually reviewed candidate PR can follow if the independent tests pass.

## Provider selection after failed experiments

The first two live Core-to-Bridge runs supplied a real `openrouter/free` route, but the dynamically chosen models produced no valid candidate. The second recorded an empty/not-usable content response from `cohere/north-mini-code:free`. The subsequent attempt uses two **explicitly free** routes already demonstrated on BEAN Core's separate 7/7 Python repair trials: `nvidia/nemotron-3-super-120b-a12b:free` followed by `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` only if the first returns an invalid edit plan. This is not a paid fallback. The model receives only exact excerpts of relevant source, while the host continues to validate against the entire pinned module. The hidden acceptance test remains unseen by both models. Actual novel repair ability has to be earned by the independent Bridge CI jobs.

## What qualifies as proven progress?

A genuine model response, a hashed candidate produced from its concrete edits, a preexisting red baseline, positive full-suite and untouched-oracle results, and fresh hidden metamorphic acceptance on both platforms. Model parse errors, HTTP 402, incomplete responses and untouched source count as **unsuccessful attempts**. A green author job does not certify a code fix.

The experiment is a functional research bridge, not proof of general intelligence, generalized code discovery, or a production ERP business-calendar definition. Source-completeness records remain upstream assertions, not externally authenticated facts.

## Ownership and peer-review arrangement

The Bridge developer owns reporting invariants and synthetic test generation, and the Core developer owns the self-writing engine and persistent improvement history. Core's peer review [PR #33](https://github.com/danieloculus0-bot/BEAN/pull/33) provides an asynchronous feedback channel. We will exchange GitHub run URLs, test output hashes, and signed-by-test-runner receipts rather than presuming that peer messages themselves are independently verified.

The original human-assisted [Bridge control PR #22](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/22) stays unmerged and is **not** fed to the model. It cannot count toward BEAN's autonomous score.

## Offline contract tests

Run `python -m pytest bean/tests/test_bridge_peer_live_author.py -q`. No real key or network is required. Actual cross-repository inference and validation occur only in GitHub Actions with the Core repository's already-configured OpenRouter secret. Private credentials and company ERP data are not written to GitHub artifacts.

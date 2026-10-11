# Lab 017: BEAN-governed autonomous Bridge code improvement

**State:** Two distinct automated source transformations completed and merged to
BEAN-AI-Bridge- main on October 10 (America/Chicago) / October 11 (UTC), 2026.
These are real code modifications, not just proposals. They are **bounded**
transformations from an explicit approved catalog, not unconstrained LLM
program synthesis or demonstrated open-ended software self-improvement.

## Working architecture

1. The trusted Bridge host inspects its own source and tests, and runs a
   concrete baseline witness showing a defect or inefficiency.
2. BEAN's reusable `bean.optimization.selection.rank_improvements` scores
   opportunities by impact, reproducibility, confidence, risk, and test
   readiness. Candidates require evidence references.
3. The existing BEAN `SelfOptimizationGovernor` records the selected
   proposal, its intended benefit and validation/rollback criteria, and the
   trusted host's scoped sandbox approval.
4. A distinct Bridge executor performs one reviewed source transformation
   on a CI checkout, never direct-to-main. No unrestricted shell, network,
   trading, motion or generated executor commands are accepted as proposals.
5. The executor reruns the full tests, checks an independent before/after
   witness, restores original source bytes on failure, and writes a receipt.
6. GitHub Actions pushes the validated source to its own branch, and a
   reviewable PR is merged only after independent cross-platform checks.
   The repository's current Actions setting blocks bot-created PRs, so
   ChatGPT's connected GitHub account opened the PRs after verification.

## Two source changes with receipts

| Source improvement | Selected evidence | Baseline | After | Verified PR |
| --- | --- | --- | --- | --- |
| Reject invalid direct Observation dataclass writes into the ERP ledger | Old ledger accepted an invalid timestamp | 70/70 tests pass but defect reproducible | 74/74 tests pass; invalid timestamp rejected | [Bridge #15](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/15), [agent run 38104281339](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38104281339) |
| Cache latest-entity parsed datetime during winner selection | Original code did 22 parses across eight records | 74/74 tests pass | 76/76 tests pass; eight parses across eight records, approximately 64% fewer calls in the fixture | [Bridge #17](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/17), [agent run 38104400893](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38104400893) |

Both source PRs passed the Bridge's Windows and Ubuntu test workflows
before merging. Code, tests and the independent BEAN execution receipts
are linked rather than recreated as imagined outputs.

The first agent push revealed two real workflow defects: it staged
generated `__pycache__` bytecode and GitHub Actions was not permitted to
create a PR. The cache entries were removed before promotion, and
[Bridge PR #16](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/16)
added precise staging, ignores, duplicate-PR suppression and an explicit
manual PR handoff when blocked. These failures remain part of the evidence.

## Limits of the evidence

- BEAN **ranked** competing source opportunities using a deterministic
  evidence-weighted algorithm. It did not invent either new patch strategy.
- The Bridge executor **generated, applied and tested actual source code**
  autonomously from two pre-reviewed transformations.
- No live ERP data were used or exposed; tests exercised synthetic fixtures.
- There is no proof of broad unbounded source refactoring, independent novel
  algorithm discovery, AGI, full unattended infrastructure maintenance or
  general-purpose autonomous software engineering.
- GitHub's daily schedule will evaluate remaining candidates, but when this
  small catalog is exhausted it will report no eligible work, not fabricate
  or manufacture a pointless diff.

## Lab 018: research direction, not production capability

The next discriminating experiment is to present BEAN with **unseen**
code failures and independently evaluate whether it can propose a novel
candidate change not drawn from the fixed Lab017 catalog.

Essential acceptance criteria:

1. An independent defect generator supplies previously unseen cases and
   hides the expected patch.
2. BEAN receives a bounded, read-only code and test context plus evidence
   from a failing reproduction.
3. A replaceable model may draft a patch under a strict structured contract,
   but the proposed text is never itself authority for execution.
4. The host applies it only in an isolated environment without deployment
   secrets or live systems, with file/path/type/size restrictions.
5. Independent regression and holdout cases measure correctness,
   usefulness, regressions, test-suppression attempts and work budget.
6. Any successful improvement is submitted as a PR with independent
   evidence, source identity and reversible diff. Failed proposals remain
   visible as failures.
7. Separate generation, validation and publication permissions so no
   untrusted model-written code runs with a GitHub write token.

Until this passes, treat Lab017 as **bounded autonomous code improvement**
rather than autonomous general software development.

# BEAN Lab 017 | Two independent paths, one evidence dialogue

This is a research implementation of **cross-branch peer development**. It is not a claim that two ChatGPT chats can communicate directly or that BEAN already autonomously rewrites production code. The shared medium is **GitHub commits, PR comments and CI artifacts**, which both sessions can independently inspect when invoked.

## Two paths deliberately kept independent

| Path | Owns | What it must *not* do |
| --- | --- | --- |
| **Selector**: [PR #32](https://github.com/danieloculus0-bot/BEAN/pull/32), branch \`feat/agentic-improvement-selection-20261010\` | Evidence-based ranking of candidate defects/changes using impact, reproducibility, confidence, risk and test readiness | Execute arbitrary changes, claim that rankings prove benefit, overwrite a validator branch |
| **Builder + validator**: this Lab 017 branch | Draft a bounded \`CodeCandidate\` from a replaceable proposer, save it only in a disposable workspace, independently run adversarial tests, and return a pinned challenge/result transcript | Write to \`main\`, modify PR #32's source files, execute model-generated code on a production host, self-certify a result as independently authenticated |

A future BEAN autonomous loop is then:

1. **Detect** a demonstrated issue with an independent test/evidence ref.
2. **Select** the most promising low-risk candidate using PR #32's module (when approved).
3. **Draft** a changed Python module with a replaceable proposer. The proposer can be an LLM; current CI uses an *explicit deterministic stub*. Code is bound to exact original text digest, branch and SHA.
4. **Challenge** the draft from a separate validator checkout, on new tests the proposer did not write. A passed fixture does not mean success across the whole repository.
5. **Report** a challenge or result with source digest, exact code-commit SHA, CI URL, test references, and prior transcript digest.
6. **Revise or abandon**; keep failed variants as evidence. A successful experiment can produce a reviewable PR, but merging to production remains a separate authorization.

## First independent cross-branch test

CI checks out the **other branch** at the exact pinned commit \`a772c41db9b38580c1532565086a071f82dc02a0\`, then runs **seven independent adversarial selector tests** from this branch. These check missing evidence, invalid scores, non-repeatable candidates, deterministic ties, risk caps and no execution functions. The selector's own tests are not used as the independent oracle.

A successful CI job creates a \`peer-selector-receipt-*.json\` evidence artifact containing the candidate source hash, exact selector commit, validator commit, GitHub run link and a three-step proposal → challenge → reported result transcript. Re-run against a changed selector commit after separately reviewing its new diff; never silently switch to the moving branch HEAD.

The four-platform peer-protocol matrix separately verifies integrity/replay, writes only to newly created local scratch directories, no stale-base code changes, and no promotion hooks.

## Persistent cross-chat handoffs

Each envelope contains \`role\`, \`kind\`, source \`branch\`, pinned \`commit_sha\`, \`subject\`, \`evidence_refs\`, optional \`candidate_sha256\`, previous message digest, and test status. The ledger enforces causal order and detects modifications/reordering; it can serialize and restore across sessions. Every CI label is deliberately **reported_pass / reported_fail / unavailable**, not unilaterally verified. An external consumer must confirm the repository, commit and run authorization through GitHub.

**A GitHub comment is the conversation.** One session posts the candidate ID, source SHA and challenge request to the PR; the other session reads it later, tests the pinned revision and replies with the evidence. There is no hidden live channel between ChatGPT threads, and no scheduled polling is enabled here.

The ledger has no distributed locking; GitHub branch/PR updates are the conflict-control mechanism. Two independent writers must not directly race to overwrite one JSON file. SHA-256 chains detect ordinary accidental changes but do not authenticate an attacker who can replace the file and its hash.

## Scope and limitations

- \`CodeCandidate\` is a **draft**; it can be created from provider text, syntax-checked, diffed and written to a new scratch folder. It is **not executed** by the module. Syntax validity is not correctness or safety.
- The first CI uses deterministic code drafting and test selection, not proof a real LLM model wrote an effective repair.
- The independent challenge does not automatically grant execution, delete branches, run arbitrary new test commands, push a PR, or merge anything.
- A GitHub CI checkout may use an ephemeral runner. The source-hash and Python checks are not an operating-system security sandbox.
- Protect real keys and confidential user data; do not put them in tests, generated code or public build artifacts.
- The selector is a parallel effort. This branch cannot assume its PR is merged until it is reviewed.
- Independence also requires fresh, withheld problems later; these seven documented checks test interface correctness, not improvement quality.

## Reproduction

From this branch, with Python and pytest installed:

    python -m pytest bean/tests/test_peer_dialogue_lab017.py -q

For the independent selector tests set \`BEAN_SELECTOR_MODULE\` to a separately checked out copy of the pinned PR #32 file, then run:

    python -m pytest bean/tests/test_peer_selector_challenge_lab017.py -q

No model credentials, network or private files are required to run the local protocol tests.

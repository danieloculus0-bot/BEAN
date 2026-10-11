# BEAN Lab 018 — Three paths, equal contradiction and complementary evidence

## Why a third path?

Two developer channels can mutually reinforce an untested assumption. The new **Path C** is an independently versioned falsification and longitudinal learning route. It has no authority over the other two, and every path must expose BOTH its positive claim and a meaningful opposing claim, PLUS a complementary next check, on exactly the same observation.

| Path | Current implementation | Standing |
| --- | --- | --- |
| **A: Select** | [BEAN Core selector #32](https://github.com/danieloculus0-bot/BEAN/pull/32) (merged) | Equal vote, same synthetic training/evaluation budget |
| **B: Build/challenge** | [Lab 017 #33](https://github.com/danieloculus0-bot/BEAN/pull/33) (draft) | Equal vote, same budget |
| **C: Falsify/compare learning** | This Lab018 branch | Equal vote, same budget; may disagree with A or B |

**Important distinction:** these three *software development paths* exist in GitHub. The three learners in the first Lab018 benchmark are **three independent deterministic synthetic policy states**, *not* three independent LLMs, live chats or conscious agents. The protocol uses the actual A and B Python files at reviewed/pinned commits in a separate CI job; independent LLM-authored repairs require later empirical testing. “Path” here means isolated code branch and evidence trail, not an always-running process.

## Symmetric dialogue protocol

Every peer receives the same observations; roles `selector / builder / skeptic` rotate A→B→C, so no peer owns the truth, memory, tests or final authority. For five matched sample cases every cycle, every peer emits:

- **Claim**: improvement likely OR regression likely, with estimated probability.
- **Counterclaim**: the opposite might still be true, including the strongest contradicting feature.
- **Complementary check**: a proposed independent test of the contradicting evidence.
- The case ID, role and explicit `verified_fact: false`, `test_result_status: not_run`.

A disagreement can be correct, false or unresolved. **Majority opinion cannot convert unverified labels into truth.** The evaluator measures pairwise agreement, proportion of unanimous errors, minority correct dissent, and whether probability outputs genuinely differ.

## Longitudinal comparison: SAME test AND FRESH test

The program evaluates exactly **seven checkpoints (0–6)**. All three peers have the same seven input features and identical learning algorithm, training batch, feedback availability and training budget (144 new labelled synthetic training cases per update; six updates). Their **initial weights differ intentionally**, allowing testable dissent without granting one participant a special privilege. The source evidence labels are evaluator-provided fictional oracle outcomes.

At every checkpoint, each learner is tested on:

1. **Same immutable 140-case fixed control**: its inputs/truth never change, are never used for training and are re-evaluated identically at every checkpoint. This detects improvement or forgetting on the exact same questions.
2. **Fresh, independent 140-case holdout**: never used for training, with a source-reliability shift starting at round 4. This tests transfer and response to a changing environment.
3. **Frozen personal baseline on both panels**: initial weights held constant while the trainable model updates. This separates improvements associated with learning from some distributional effects.
4. **Peer distinction and contradiction**: does A, B or C supply a uniquely correct dissent, do all three confidently agree on a wrong answer, and do differences persist after equal training?

Record accuracy, Brier score, precision/recall, revision weights, fixed accuracy delta, fresh-vs-frozen delta, disagreement, unanimous-error rate, correct minority dissent, per-cycle training count, exact repeated panel fingerprint, fresh panel fingerprint and all claim/counterclaim/checks. Negative changes MUST be included. Neither fixed nor fresh holdout labels are ever shown to a learner for updating. A rise on the fixed panel alone is **not** a general-learning claim; the fresh holdout and frozen comparator matter.

### Research questions (falsifiable)

- Can all three paths supply distinct reasons, rather than merely different labels?
- Does each independently adjust its weights after labelled training feedback and improve fresh accuracy and/or calibration compared with its own frozen prior?
- When source reliability changes, does a previous improvement reverse? Does useful minority disagreement help catch failure that consensus misses?
- Is there a convergence point where opinions become identical? If so, is that warranted by evidence, or merely a shared training bias?
- Does the repeated fixed-panel result improve while *new* heldout performance gets worse? That is a failure of transfer, not robust self-improvement.

## Real-branch integration

The GitHub Actions cross-path job separately checks out:

- A: merged original selection source at commit `a772c41db9b38580c1532565086a071f82dc02a0`
- B: original Lab017 builder at `84cb0681c05ec956ed2de9fbb5590a2c2e3e266e`
- C: the Lab018 code under test

It checks A's ranking result and B's candidate-diff integrity through **independently authored C assertions**. It does not allow any model-generated code to execute, self-approve a merge, or modify a peer branch. Any later hosted-model tests require an authenticated model runtime and new blind tests.

## CI and evidence

The dedicated workflow `bean-triad-lab018.yml` runs on Linux/Windows, Python 3.10/3.12 and uploads full longitudinal JSON traces. Independent multi-branch integration runs on both OSes. The regular full Core regression suite also runs. Every code improvement proposed after this point should be reported with **exact source commit/digest**, patch candidate, contradictory and complementary observations, before-and-after repeated-test metrics, *fresh* holdout metrics, and the experiment's failing cases.

**Promotion criterion:** do not merge an autonomous rewrite because one panel shows improvement. Demand actual paired unseen-case gains, meaningful negative tests, coverage and source authenticity, replay reproducibility and review of any regressions. All existing production behavior remains unchanged on this draft branch.

## Local test

    python -m pytest bean/tests/test_triad_lab018.py -q -ra
    python -m bean.evaluation.triad_lab018 --out lab018-results.json

No external model credentials, tokens, accounts, private files, hardware, or company reports are required for this first comparative synthetic run.

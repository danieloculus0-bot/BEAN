# BEAN autonomous composition research — 2026-10-25

**Scope:** A bounded, executable program-synthesis subsystem in BEAN's existing Python Core. It is not broad AGI, unconstrained planning, or automatic strategy deployment.

## The hypothesis loop

1. **Learn components separately** with the existing \`reasoning_learn_local\` interface. Each learned symbolic rule is anchored to evidence, an original domain, and a SHA-256 ID in the Core SQLite journal.
2. **Discover combinations autonomously** with \`reasoning_propose_compositions\`. BEAN enumerates pairs of retained skills from different domains and a small library of typed output joins, returning multiple *hypotheses* (not answers). Unproven proposals are not persisted as facts or chosen just for novelty.
3. **Evaluate combinations against distinct development examples** through \`reasoning_learn_composition\`. BEAN executes every possible plan, retains the unique survivor **only** if at least four unique questions support that plan and no rival is equally supported. Ambiguous or contradictory examples lead to abstention.
4. **Retain a traceable procedure** inside the existing SHA-linked SQLite experience ledger. Its receipt records both learned parent IDs, source domains, join, test-question hashes, evidence refs and the finite search size.
5. **Apply on new tasks** via \`reasoning_auto\`, \`reasoning_local\`, or \`reasoning_composed\`. The program executes both component rules in order and joins their outputs. BEAN provides a trace, rule IDs and a new inference receipt. Restart recovery replays from the original Core journal.
6. **Evaluate new problems separately** using the caller's held-out scoring. Host feedback can be recorded against the inference receipt, but is clearly labeled host-reported, never independently proven truth.

No caller gives the algorithm the chosen join or parent pair. It searches available candidate programs itself. The **user or evaluation harness still supplies examples and independent evaluation**; BEAN does not hallucinate its own success scores.

## A structured example

An existing tag rule ranks numerical tags in descending order. An independently learned gauge rule identifies a median measured value. A new problem contains both:

\`{"parts":["TASK-1 tags A3 B9 C5","TASK-2 A=12 B=7 C=19"]}\`

BEAN proposes alternate combinations such as concatenation, reverse concatenation, rank lookup and prefix/suffix extraction. Given distinct development cases in which the expected output is the rank of the median-gauge label in the tag order, its search selects \`rank_second_in_first\`: \`BCA\` combined with \`A\` gives \`3\`.

Previously unseen problems with new labels/numbers test whether the combined procedure works. The uncomposed, primitive-only baseline must abstain on the same composite questions.

## Explicit limits

- The current rule grammar is two typed inputs matching the previously implemented \`tags\` and \`gauge\` primitives; it does not understand unconstrained natural-language tasks. Candidate joining is limited to six safe functions.
- All development examples are visible during synthesis. Even success on unseen synthetic CI probes is not independent real-world or out-of-repository replication.
- Compositions may conflict. Multiple retained plans with different outputs must cause abstention, not arbitrary preference for a newer plan.
- No autonomous claims of expertise, execution privileges, wallet access, order placement, auto-promotion, retraining of unrelated frozen trading candidates or external model/API fallback are added.
- The future experimental milestone is typed knowledge graphs and multi-hop programs, followed by truly independent blind problems in software, engineering and market-research analysis with an external evaluator.

## Reproducibility

From a source checkout, without an API key:

\`\`\`powershell
python -m unittest bean.tests.test_autonomous_composition -v
python -m unittest bean.tests.test_native_local_reasoner bean.tests.test_blind_reasoning_probes -v
\`\`\`

The dedicated GitHub Actions matrix runs Python 3.10 and 3.12 on Windows/Linux, including the Core inference/restart checks. CI passing indicates bounded functionality only; it does not confer general intelligence.

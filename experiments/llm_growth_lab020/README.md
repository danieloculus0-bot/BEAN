# BEAN Lab 020: Historical Core LLM-versus-AST code growth

This experiment challenges a **frozen, genuine historical BEAN Core** selector version, not a mock clamp function. The bug was subsequently fixed in current `main`. Its test suite also checks that current Core continues to pass the original defect reproduction and holdout. The existing duplicate check treats Patch-A and " patch-a " as different identifiers, despite referring to one underlying improvement. It also treats the Unicode strings Straße and STRASSE as different. The contract for this task is strip-and-casefold uniqueness while retaining original identifiers in returned objects.

## Registered comparison

- The original source was `bean/optimization/selection.py` (historical Git blob `f95c078420ae9151cf489f326fb213d51b5716f2`), now pinned in `experiments/llm_growth_lab020/fixtures/selection_pre_fix.py`. The comparison defaults to that archived source. The LLM does not see evaluator tests.
- The same 14-case developer test panel evaluates each revision and the AST brute-force control. The AST search gets 25 trials versus a maximum of three real free-LLM proposals.
- The free OpenRouter route is the literal openrouter/free, with no paid fallback and at most one request in each of three rounds.
- After a round, the LLM only receives the original code, objective, and previous outcome, passing-test count, total, and candidate SHA; the model never receives unittest traceback or test code.
- No-secrets evaluator jobs run candidate code independently. SHA256-linked result history travels between rounds as artifacts, including failures and regressions.
- A seven-case follow-up holdout is evaluated ONLY in final comparison, never in feedback. Its file is public in the repository and thus absent from prompt but not cryptographically sealed.
- The original experimental branch included an optional GitHub review-proposal workflow; this clean promotion does not install or run that workflow. A historical candidate is not a patch request for already-fixed current Core.

Success is independently passing 14/14 development plus 7/7 holdout while preserving Core selector ranking, confidence/risk validation and output API. Other results including failed tests, provider outages and repeated identical source are recorded as evidence, not counted as progress.

Iterative prompting is not neural weight training or evidence of general recursive intelligence. A single task cannot demonstrate transfer across software domains. The final report compares best development score, unseen holdout, revisions and AST candidate scores. The historical receipts are within one GitHub Actions run; continuous cross-run memory still requires a durable restored journal.

Local nonsecret verification:

    python -m pytest bean/tests/test_llm_growth_lab020.py -q
    python -m experiments.llm_growth_lab020.lab020 ast --out local-ast --attempts 25

This experiment uses only public BEAN source and fictional test identifiers, no workplace data.

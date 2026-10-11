# BEAN Lab 020: Real Core LLM-versus-AST code growth

This experiment challenges real BEAN Core improvement selector code, not a mock clamp function. The existing duplicate check treats Patch-A and " patch-a " as different identifiers, despite referring to one underlying improvement. It also treats the Unicode strings Straße and STRASSE as different. The contract for this task is strip-and-casefold uniqueness while retaining original identifiers in returned objects.

## Registered comparison

- The original source file is bean/optimization/selection.py, copied from production main; the LLM does not see any evaluator test source.
- The same 14-case developer test panel evaluates each revision and the AST brute-force control. The AST search gets 25 trials versus a maximum of three real free-LLM proposals.
- The free OpenRouter route is the literal openrouter/free, with no paid fallback and at most one request in each of three rounds.
- After a round, the LLM only receives the original code, objective, and previous outcome, passing-test count, total, and candidate SHA; the model never receives unittest traceback or test code.
- No-secrets evaluator jobs run candidate code independently. SHA256-linked result history travels between rounds as artifacts, including failures and regressions.
- A seven-case follow-up holdout is evaluated ONLY in final comparison, never in feedback. Its file is public in the repository and thus absent from prompt but not cryptographically sealed.
- If at least one complete candidate passes all fourteen developer tests and the extra seven holdout tests, a separate no-inference-secret GitHub job can copy the SHA-verified code to a new review branch based on current main and attempt a PR, never a direct production merge.

Success is independently passing 14/14 development plus 7/7 holdout while preserving Core selector ranking, confidence/risk validation and output API. Other results including failed tests, provider outages and repeated identical source are recorded as evidence, not counted as progress.

Iterative prompting is not neural weight training or evidence of general recursive intelligence. A single task cannot demonstrate transfer across software domains. The final report compares best development score, unseen holdout, revisions and AST candidate scores. The historical receipts are within one GitHub Actions run; continuous cross-run memory still requires a durable restored journal.

Local nonsecret verification:

    python -m pytest bean/tests/test_llm_growth_lab020.py -q
    python -m experiments.llm_growth_lab020.lab020 ast --out local-ast --attempts 25

This experiment uses only public BEAN source and fictional test identifiers, no workplace data.

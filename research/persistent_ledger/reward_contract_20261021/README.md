# BEAN reward contract: durable test evidence

This research snapshot preserves the **actual case-level GitHub Actions stdout results** from BEAN's scoreboard/reward contract, rather than relying only on a green badge. It does not overwrite any prior research ledger.

- `test_cases.jsonl`: **56 actual individual unittest case observations**, seven per job over eight successful matrix jobs. Rows include test identity, pass status, operating system, Python version, source commit, workflow run, job ID and source URL.
- `scoreboard.json`: bounded summary of this particular CI campaign (**8/8 jobs and 56/56 test cases passed**, no failed cases). Schema: `bean.reward.contract.scoreboard.v1`.
- Original evaluated code commit: `caacaebd69833bf90102181c8ecbbad90d05ddea`. Workflow runs: [39539948527](https://github.com/danieloculus0-bot/BEAN/actions/runs/39539948527) and [39540021508](https://github.com/danieloculus0-bot/BEAN/actions/runs/39540021508).

**Limits:** These are identical test names exercised across two workflow invocations, not 56 independent learning episodes. The source data are GitHub Actions job logs; complete original logs were not copied into GitHub and may expire. This JSONL preserves every parsed unittest outcome from those eight jobs, not all global BEAN repository tests and not full stdout/stderr. No neural weights changed. Do not count passing regressions as autonomous learning progress. This is a pinned historical source snapshot; later commits require their own distinct records.

The experimental `bean.optimization.scoreboard_context` module can now see this scoreboard alongside the older replay, Lab009 and full-Core matrix scoreboards. Rewards are generated only from individual comparable metric outcomes, not from this aggregate test count alone.

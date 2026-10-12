# Frozen learner replication: seeds 56–58 (2026-10-12)

**Mixed, inconclusive.** PR #116, Actions run 38264886479, source 5dd011a7501e895abfb98343a6eeb49fac5bc9ed. Original learner blobs unchanged from PR #113. Windows and Linux: 8/8 unit tests each, both smoke tests successful. All three full trials completed; original Actions artifacts retained.

| Seed | Cold bricks | DQN bricks | Evolved bricks | Evolved - DQN | Survival evolved/DQN | Gate | Selected frames vs control | Updates selected vs control |
|---|---:|---:|---:|---:|---|---|---|---|
| 56 | 1.43333 | 7.06667 | 5.92500 | **-1.14167** | .24167/.38333 | Rejected | 134715/190968 | 33615/47679 |
| 57 | 1.35000 | 1.65000 | 2.98333 | **+1.33333** | 0/0 | Accepted | 151132/206592 | 37720/51585 |
| 58 | 1.35000 | 2.66667 | 11.90000 | **+9.23333** | 1/0 | Accepted | 169230/217430 | 42244/54294 |

Paired raw mean +3.14166 bricks/game, sample SD 5.41874, t 95% CI [-10.31923, +16.60255] across n=3 independent training seeds. Gate-adopted mean +3.52222. Pooled descriptive six-seed results (53–58): 4/6 positive, mean +2.31111, SD 5.44991, t 95% CI [-3.40822, +8.03044]. **Not established as reliably superior**; uncertainty spans zero.

Actual results.json, final-evolved-weights.json and evolution.sqlite were downloaded and checked. Each SQLite PRAGMA integrity_check returned ok; each 9-event journal chain was recomputed and verified against its recorded tip. Final weights SHA-256 matches recorded final_policy_sha256 for every seed. The ZIP digests were independently verified against GitHub artifact digests.

| Seed | Final weights SHA-256 | results.json SHA-256 | Journal tip | Artifact ZIP SHA-256 |
|---|---|---|---|---|
| 56 | 1621d00615321ed81f2c46f3282492b1d70e0b246697029a664f3b626ed6a21c | 98bbd5eac49a6d3f327a19811c5049755329b0f3e95d50054448dda904da7bd2 | ef72ab43899cfd1047d14b7e14fd78b1c4b62d36a00272e2b78ef5ade58fa704 | e25a0f66405a22d0017c68451ca5e7d913c7386f68699addecf8e06b56efe894 |
| 57 | 72850c11487f6cb0e5d335391364d07c9de2b34d3f5c4caf696598a905181aa3 | 91dee9e6187112fab4e8e11fdff00c0e993f334e626a6e3502d0c7fb75accab6 | 7f209e086d78ca997d6ef4f7d37446afcc8018ef0aa3e58bc500cd45560c303b | 06a09c2f5e65bb7ac46e8dcaadd0e02b7f05c490c990ac22eed007b4b51551f2 |
| 58 | c33011a52b64c3b516c50ebde493943ff389fac60b8a8a0a59d9d5be79abb86c | 9db070b5db8babda99619dc298a3f27766b383bb26fcc878e780c62e665d5046 | ce7f00c688c6fb10e67ed219775b616434228c84e7574df1ccd0c7582b2c0776 | 51e180cc80ba72a88c4a6bb8146073790d72430e15e1f17f7263aa178a53f81f |

Artifacts: https://github.com/danieloculus0-bot/BEAN/actions/runs/38264886479

Limitations: selection cohorts reused in gate, unmatched frames and gradient updates, engineered 3-feature Breakout not pixel Atari, only three new training seeds. All 41–58 now seen. Next: preregister a **frozen, no-tuning** replication on fresh 59–61; no Main merge, live trading, or hardware control.

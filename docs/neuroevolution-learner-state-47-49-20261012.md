# Learner-state inheritance replication: seeds 47–49 (2026-10-12)

**Verdict: negative, 0/3 evolved-vs-uninterrupted-DQN wins.** This is an archived experimental result, not a learning gain. Prior results for seeds 41–46 remain preserved in their original GitHub Actions artifacts. Do not train or retune on 47–49 holdouts again.

## Provenance
- Research draft PR: #110, CI run: [38247985900](https://github.com/danieloculus0-bot/BEAN/actions/runs/38247985900)
- Tested head commit: `d8c5bb9504362596dcee5d103d624ce6a9ef58b2`
- Original parent hypothesis: guarded evolution PR #107, `2eb05f655cbefce888fc38316a24cfb52b571deb`.
- Research change: offspring inherit online+target weights, replay, optimizer state, RNG, learning counters; parent weight hashing fixed for tensor-bearing snapshot.
- Ubuntu job `114806618577` and Windows job `114806619083`: five focused tests each passed, including full-state inheritance and journal round trip; bounded seed-41 *smoke only* passed. Source assertions and job logs, not only check conclusions.
- Replication jobs `114807101028` (47), `114807101273` (48), `114807100961` (49) all completed successfully. Successful jobs do NOT mean improved learners.

## Preregistered protocol and observed holdout

Each training seed uses 3 generations × 3 candidates × 70 games = 630 episodes total across candidates, compared with uninterrupted DQN trained on 630 episodes of the same environment-seed multiset. Selection uses validation; before holdout, the unchanged two-cohort promotion gate requires evolved gain >=0.25 bricks/game and survival drop <=0.05 on **both** separate 60-game validation cohorts. Holdout is 120 new episodes per policy. The training and holdout seeds are separate. Episodes are matched; **frames and gradient updates are not matched**. The validation cohorts are reused in candidate selection, so the gate is NOT an independent third-party validation.

| Train seed | DQN bricks/game | Evolved bricks/game | Evolved minus DQN | DQN survival | Evolved survival | Gate | DQN frames/updates | Selected frames/updates |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| 47 | 10.48333 | 4.11667 | -6.36666 | 0.98333 | 0.11667 | Reject | 156218 / 38991 | 26753 / 6625 |
| 48 | 2.86667 | 2.45833 | -0.40834 | 0 | 0 | Reject | 217260 / 54252 | 18923 / 4667 |
| 49 | 10.73333 | 10.18333 | -0.55000 | 1.00000 | 0.77500 | Reject | 254667 / 63603 | 32643 / 8097 |

- Mean raw gain **-2.44167 bricks/game**, standard deviation ~3.39988; naive seed-level Student t 95% interval **[-10.88744,+6.00411]**, n=3. Too imprecise to claim a general effect.
- Mean evolved-minus-control survival **-0.36389** (36.4 percentage points).
- The gate rejected all three; adopted policy was ordinary uninterrupted DQN for each, and adopted relative gain was 0. This shows a functioning rejection gate, not improved evolutionary learning.
- Validation gate deltas for 47: bricks -6.55/-6.80; survival -0.90000/-0.96667.
- Validation gate deltas for 48: bricks +0.23333/+0.51667; survival 0/+0.01667; first cohort missed +0.25 threshold.
- Validation gate deltas for 49: bricks -1.21666/-0.76667; survival -0.35/-0.25.
- The selected evolutionary lineage experienced far fewer frames than uninterrupted DQN, despite episode-budget parity. This is a plausible contributor, not yet a demonstrated cause.

## Immutable source/receipt references

| Seed | results.json SHA-256 | selected model SHA-256 | journal tip |
|---|---|---|---|
| 47 | `21ce5acb30caeb978ff9b5188b0f938b5149f26ed081d68994dce54694ea1a02` | `7126cbc515f18a7c8486e17273b15d409538598dc456011d230ba8fd216325a6` | `4aa0efab1eacc5826ba7adcd91803bd09e00a60c6d9e46b945a11a06255a4a52` |
| 48 | `539900580d7552a3cbfc4dcb0871d388d9a1795a976b1b237c529c858279990c` | `3902e3c9f27f26c20849cdeae3975ad805cbc4ffe4c5fe3a1868cd270c6b2849` | `bcc222726552a8a3b0a0b9ef047c895114591ea317328465aa7451b1a53c026b` |
| 49 | `60f0c00146e20cc7ac10248fe4e9b165aea7eccedfd81e9fc626bdddd636fcc1` | `a095af5d24e9e968aa172f0ebffa24f2eff6010b04e85e54060a436872ac5bb0` | `155e4f6f88644a57af9b5fe04d94181edf69b108ef74cd06ae3dfbd3f880347e` |

Artifact archive SHA-256: seed 47 `2a61385643e08df3a997baf6df93d060fb6969aec7b2a665cffceaf1b6313108`, seed 48 `5d5e88284a9164277b095d47aad963f942ea8bf46f13a17d681ba520f054839f`, seed 49 `b7fc3960550e95487e75e564257016f713c2966ef7f6d83c6ce3cf4434d8e1c7`.

Each artifact contains `results.json` and `evolution.sqlite`. Archive-level integrity, source hash, individual result checksums, and unchanged negative evidence are retained. No Main merge or public learning-gain publication is authorized.

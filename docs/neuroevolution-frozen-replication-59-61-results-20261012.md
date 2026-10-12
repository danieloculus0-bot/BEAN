# Frozen potential replication 59–61: independently verified results (2026-10-12)

**Status: MIXED/NEGATIVE, NOT PROVEN SUPERIOR.** PR #117 draft; source commit `e4fbc725466f8fa6ebcd28e13e599c515a4f254e`; GitHub Actions [run 38266446388](https://github.com/danieloculus0-bot/BEAN/actions/runs/38266446388), completed 2026-10-12 15:00 UTC. Preregistered in `docs/neuroevolution-frozen-replication-59-61-20261012.md`. Frozen source blobs verified unchanged: evolve.py `6b442cca54e6d5c080af959e5bbd87fd274b8d97`, sponge_dqn.py `769da37ac2e13566ddc0d83c770d7323cbfc0da7`, test_evolve.py `2841b1840ea8ce6df67fc3c9441c3dd6f14b77fe`.

Linux and Windows focused unit tests each passed 8/8 and bounded smokes completed. I downloaded all three complete trial artifacts and inspected their `results.json`, `final-evolved-weights.json`, and SQLite journals. Each ZIP SHA256 matches GitHub's artifact digest; each SQLite `PRAGMA integrity_check` is ok; each nine-entry SHA256 journal chain recomputes exactly to the recorded tip; each final weights JSON SHA256 matches `final_policy_sha256`.

| Seed | Cold bricks | DQN bricks | Evolved bricks | Raw evolved - DQN | Adopted - DQN | Survival evolved/DQN | Gate | Evolved frames / updates | DQN frames / updates |
|---|---:|---:|---:|---:|---:|---|---|---|---|
| 59 | 1.45000 | 3.70833 | 4.58333 | **+0.87500** | +0.87500 | .00833 / 0 | Accepted | 181694 / 45360 | 159671 / 39854 |
| 60 | 1.34167 | 10.99167 | 2.89167 | **-8.10000** | 0.00000 | .00833 / 1.00000 | Rejected | 177709 / 44364 | 214363 / 53527 |
| 61 | 1.02500 | 2.55000 | 2.75000 | **+0.20000** | +0.20000 | 0 / 0 | Accepted | 191591 / 47834 | 189077 / 47206 |

**Independent seed-level statistics:** raw evolved-minus-DQN n=3, mean **-2.34167**, sample SD **4.99827**, Student-t 95% CI **[-14.75806,+10.07473]**. Gated adopted-minus-DQN mean **+0.35833**, sample SD **0.45848**, t95 CI **[-0.78061,+1.49727]**. Historical frozen 53–58 n=6 mean +2.31111. Combined frozen 53–61 n=9, 6 positive / 3 negative, raw mean **+0.76018**, sample SD **5.49738**, t95 CI **[-3.46548,+4.98584]**. None establish reliable superiority.

Each seed: 270 candidate search games plus 360 champion continuation, compared against 630 uninterrupted DQN games on the same training environment seed multiset. Two disjoint 60-game validation cohorts are reused for preholdout gate; each evaluated arm uses 120 paired sealed holdout games. **Training frames/updates are unmatched**, validation reuse can overfit, engineered-state Breakout is not pixel Atari, and 3 new seeds are underpowered.

| Seed | results.json SHA256 | final-evolved-weights.json SHA256 | Journal tip | ZIP SHA256 |
|---|---|---|---|---|
| 59 | `19ed137eaedc6856170f034671c4377f57422c077c196740d16eb390ec7c023b` | `5c08aea0a0ba7fe882118b373a0b6b6b78a14297cd38b0c7632a27bfe70a5c18` | `0bc6076f2b9888411b97d4d59229a2c263f26e406081d2a1d902905e97e004a1` | `843b1ef6d8c56574bb9d65bee8020077e7c14fb8d0eafdfb6e15fce9b092990d` |
| 60 | `992efe3ff5c2f27f4ff9e2a8483cb65d673580a76d2d40ecb68a5a64ae57e25d` | `86cc8b9086c6a6bc046595d5173e98c9f69e9873a8f91c328dcb12877da6b2d0` | `a5c63e61f30370744e60bac7c28933fdec5923917d4d153d2e25afb0123e326f` | `d03d65f51779acd90fb5865e21576baed5a8190ea8e88a1f86e1a89762722014` |
| 61 | `c541634551431a7406c90b0ed06af0d3a316a8fbf411393c85afddb5a8a3c6e6` | `66d46ef23a2a33f7e6f5c56cf58d1cd8b16b93bd6e0669d916bcc364c4bd525f` | `fba4070a53e7ba289bcda79a81008b2d3f59915fd30ffcb31e2a658752a677c9` | `daf2131076c63d3f9044def8e39b3b8b4aefc08629c30b20145de20d5a78b179` |

**Decision:** leave frozen PR #117 draft; preserve the catastrophic seed 60 failure. No Main merge, no performance claim. The separately preregistered next bounded research modification is linear continuation shaping annealing on fresh seeds 62–64 with an exact-source frozen control.

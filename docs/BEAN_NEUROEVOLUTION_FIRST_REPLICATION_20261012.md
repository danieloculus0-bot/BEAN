# BEAN Neuroevolution: first three training-seed replication

**Date:** 2026-10-12  
**Source:** [GitHub Actions run 38228577943](https://github.com/danieloculus0-bot/BEAN/actions/runs/38228577943)  
**Conclusion:** Evolutionary advantage **NOT REPLICATED**. Functional neural evolution is tested, but performance optimization is unreliable.

The Windows and Ubuntu smoke jobs passed the implementation contract. The independent training-seed qualification ran with three seeds, each training 3 generations x 3 agents x 70 Breakout episodes, evaluating on 60 selection games and 120 sealed final games. Three author/judge test jobs completed successfully. A successful CI result is *not* a winner verdict.

| Train seed | Cold | Uninterrupted DQN | Evolved DQN | Evolved minus DQN | DQN survival | Evolved survival |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 41 | 1.14167 | 10.68333 | 6.15000 | **-4.53333** | 96.667% | 19.167% |
| 42 | 1.33333 | 10.87500 | 2.24167 | **-8.63333** | 99.167% | 0% |
| 43 | 1.25000 | 1.50833 | 2.32500 | **+0.81667** | 0% | 0% |

**Mean evolved-minus-standard DQN:** -4.11666 bricks/game across the three training seeds. The seed-to-seed dispersion is high; statistical confidence with three training seeds is limited. All comparisons use the same 120 held-out game seed set within each training-seed stratum, but the original evolutionary search selected on only one 60-game validation set. The comparator was not considered as a validation-time champion. This is a structural weakness of the search, not evidence of general learning.

**Research response:** Introduce a second disjoint validation cohort for each candidate, cross-cohort minimum fitness, and a final pre-holdout promotion gate comparing the best evolved candidate to a full-budget conventional DQN on both validation cohorts. If it does not win on both, the gate must reject its adoption, while still documenting the failed experiment. The already-viewed seed 41–43 holdouts cannot serve as pristine evidence for that updated method: run fresh independent training and holdout seeds.

**Interpretation:** The network demonstrably updates weights, offspring inherit/mutate weights, and hashes record the evidence. Evolution of the training strategy is not yet shown to help on average. Do not promote this as a BEAN intelligence gain or merge to Main.

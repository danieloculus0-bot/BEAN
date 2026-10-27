# BEAN learning from actual CalculiX results, not invented FEA answers

**Implemented:** BEAN now has a reproducible, geometry-separated real-native FEA training/evaluation harness, [`bean/engineering/native_fea_learning.py`](../bean/engineering/native_fea_learning.py).

**[Run the actual BEAN ↔ EZ-FEA learning workflow](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-real-fea-learning.yml)**. Only report measured outcomes from a **completed** workflow. The initial source-code commit and setup alone do not mean 42 FEA simulations finished.

## Actual physics dataset

Source: current EZ-FEA `main`, [`ezfea.native_learning_cases`](https://github.com/danieloculus0-bot/EZ-FEA/blob/main/ezfea/native_learning_cases.py).

The scripted native curriculum specifies **42 physical 3D CAD cases**, with **12 calibration/training geometries** and **30 separate unseen geometries**:

| Family | Target read from real CalculiX output | Independent approximation | Train | Holdout |
|---|---|---|---:|---:|
| Axial tension/compression, varying box lengths/widths/heights, E and force | Fixed physical midspan C3D10 `abs(sigma_x)` (MPa) | `abs(F)/(width*height)` | 4 | 10 |
| Cantilever bending, changing span, depth/width, E and force direction | Peak actual nodal displacement (mm) | `abs(F)*L^3/(3*E*I)` | 4 | 10 |
| Round-shaft torsion, different lengths, radii, E, nu and torque direction | Actual fitted end twist from C3D10 nodal displacements (rad) | `abs(T)*L/(G*J)` | 4 | 10 |

All real labels are obtained from native `.dat`/FE result extraction; the code also archives physical source STEP, solver input, force/reaction checks, source STEP hashes, and full CAD/solver traces. The entire training run **fails closed** if any specimen lacks a trustworthy native result; failed cases are recorded on disk first, never silently skipped.

The `train` and `holdout` groups have **disjoint geometry signatures**. Different loads on exactly the same CAD geometry **do not qualify** as unseen geometry. Held-out results never enter rewards. Three families are related by basic linear elasticity but have physically different stress/displacement mechanisms; the task is *bounded calibration*, not general autonomous engineering intelligence.

## First-run lesson: an engineering-rule error, not just a learning error

The first full [42-case native run](https://github.com/danieloculus0-bot/BEAN/actions/runs/40425518608) **did execute** all native specimens, persist 60 SpongeTD Q updates and score 30 unseen geometries. It measured 10.60% uncorrected reference error versus 8.76% BEAN correction error, with **checkpoint promotable = false**. Crucially, bending alone was badly mispredicted.

Investigation identified a **wrong-axis cross-section inertia** in the original nonsquare bending reference. Each CAD bar is long in X, has width `b` in Y and height `h` in Z; a transverse **Y** load bends about **Z**, so the correct second moment is **`I_z=h*b^3/12`**, not `I_y=b*h^3/12`. This produces a major artificial error on nonsquare cross sections, especially if `b/h` differs substantially from one. [The corrected source](https://github.com/danieloculus0-bot/EZ-FEA/blob/main/ezfea/native_learning_cases.py) and a 4×-difference regression test now explicitly enforce the physical axis.

**Do not promote or reuse the earlier Q checkpoint as an engineering correction.** It was trained in part against an incorrectly selected analytical axis. Instead regenerate all 42 real source cases, train a fresh policy, compare again on the same prespecified unseen CAD geometries and retain both outcomes. This is a concrete lesson in preferring corrected first-principles physics to learned compensation for a bad equation.

## What BEAN actually learns

BEAN's **existing** `LearningRuntime` / SpongeTD Q policy receives five candidate analytical corrections: the unadjusted reference, ±2%, ±6%. Each of the 12 **real** training measurements is compared with all five candidates, producing **60 genuine measured-error Q updates** (as opposed to a reward from a toy beam simulator). Each action is recorded with the CAD source SHA, observed actual FEA result, reference formula output, relative error, and reward.

After training, BEAN makes a *frozen greedy choice per physical loading family*, without knowing the numerical targets for the reserved geometries. The separate evaluator reveals those real solver targets only for scoring. Both methods use the **same measured source**:

- Average relative numerical error for uncorrected classical mechanics.
- Average relative numerical error for BEAN's learned bounded correction.
- Agreement with explicit **example-only numerical screening thresholds** and named low/high-error cases.
- Per-family results, signed root-cause classifications, and full performance ledger (including regressions).
- SHA-linked BEAN `SpongeTD` persistent Q checkpoint, restored and checked after the process restarts.

The scoring procedure requires **at least 30 real holdout cases** because that is the existing BEAN scored-checkpoint minimum. A recorded checkpoint does not imply `promotable=true`; check the actual measured score. No learned policy is automatically substituted for independent mechanics, the native FEA engine, or a field tool.

## What this does *not* prove

No real material fracture, yielding, buckling, connector failure, weld/bolt rupture, nonlinear contact, code design limit, inspection approval or test-coupon result is included. An “exceeds example threshold” label is a **hypothetical exercise**, *not* proof of construction failure. FEA-to-theory error also includes boundary conditions, mesh recovery error and continuum approximations—BEAN should not blindly memorize corrections as physical laws.

The main development paths are **verified failure-mode classification**, **geometry and fixture generalization**, **full assembly interface reactions and contact stress**, and **comparison to physical test data and external benchmarks**. A new material or assembly family must demonstrate its own independent held-out performance before BEAN issues a quantitative correction.

## Exact repeatable commands

From BEAN repository root, with current EZ-FEA checkout and native mesher/solver available:

```bash
PYTHONPATH=../EZ-FEA python -m ezfea.native_learning_cases --out real_fea_corpus
python -m bean.engineering.native_fea_learning real_fea_corpus/native_curriculum.json --out bean_native_training
```

Both output folders preserve the full original data. [CI artifacts and comparison table](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-real-fea-learning.yml) are retained for a bounded GitHub Actions period; the original reports can be regenerated from the tracked code and fixed specimen specs. Their source provenance is *host-attested*, not cryptographically authenticated by BEAN itself.

**Release status:** real native training and numerical held-out evaluation, **engineering validation not established**.

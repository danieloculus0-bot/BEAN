# BEAN Jobsite: engineering answers without engineering-software menus

**Purpose:** an operator-facing tool for simple lumber quantities and preliminary structural load screening, backed by BEAN's own deterministic equations and its existing feedback-learning system.

This is the first narrow design-engineering skill, not a replacement for a structural engineer or a full assembly FEA analysis.

## What the field operator sees

The local UI has just two jobs: **Count 2×4s** or **Check a beam**. Controls are large, high-contrast and usable with a simple browser on the local computer running BEAN.

### Start

From the root of the [BEAN repo](https://github.com/danieloculus0-bot/BEAN):

```bash
python -m bean.engineering.jobsite_web
```

Open **http://127.0.0.1:8765** on that computer.

There is no subscription key, model provider, internet requirement, or decorative chatbot. The webpage calls `/api/calculate`, which executes the *actual* `bean.engineering.jobsite` Python engine.

**Deployment limitation:** the lightweight service intentionally listens on 127.0.0.1 only. It is **not** yet an authenticated HTTPS service for multiple tablets or phones. Do not expose its development listener directly to a shop network. That requires a secured host/connection.

### One-time project setup for beam checks

A responsible designer or engineer must provide the adjusted material bending/shear limits, elastic modulus, deflection criterion, and the source they came from. BEAN does **not** invent these based on a label like “2×4.”

```bash
python -m bean.engineering.profile_setup --out jobsite-project.json
python -m bean.engineering.jobsite_web --profile jobsite-project.json
```

The setup asks for the project name, design-reference source and four values. A reviewer should verify the saved JSON. After the profile is installed, those values are hidden from the operator's everyday beam form; browser requests cannot overwrite them.

For keyboard-only use:

```bash
python -m bean.engineering.jobsite
```

### Simple wall example

**Straight wall, 20 ft, 16 in on center, without openings:** `ceil(20×12/16)+1=16` full-height studs. The estimate intentionally excludes bottom/top plates, intersections, doubled corner studs, headers, jack/cripple studs, lateral bracing, waste, and all structural load checks. Doors/windows trigger an error rather than a guessed estimate.

### Beam explanation

For a *simply supported rectangular beam under uniform distributed load*, BEAN calculates:

- Bending moment `M = w L² / 8`, bending stress `M / (b h²/6)`
- Reaction shear `V = w L / 2`, approximate max shear stress `1.5 V / (b h)`
- Elastic midspan deflection `5 w L⁴/(384 E I)`, where `I = b h³/12`

All input dimensions are *actual* inches, `w` is lb/in after conversion from lb/ft, `E` is psi. BEAN compares each computed result against **user-supplied** allowable limits, identifies the governing criterion, and ranks members by the **highest limit utilization**, not simply smallest physical size.

When a limit is exceeded, its mitigation list identifies higher section stiffness, a properly supported shorter span, and verified load reduction. It also computes a **theoretical depth threshold** under this *idealized model*, not a purchasable or authorized structural section. Any actual change must re-check support reactions, connection strength, bearing, bracing, structural stability, building loads and material adjustment factors.

## How BEAN was taught

- [Versioned construction rules](../bean/engineering/construction_rules.json) distinguish supported formulas, required inputs, exclusions and *no automatic code approval*. They contain no imaginary adopted-jurisdiction span tables.
- [BEAN Jobsite math](../bean/engineering/jobsite.py) performs the real quantity and member calculations.
- [BEAN circular-shaft stress reference](../bean/engineering/stress_solver.py) separately handles elementary axial, bending and Saint-Venant torsion stresses.
- [Engineering mitigation learning](../bean/engineering/mitigation_training.py) invokes the existing **SpongeTD Q learner**, chooses constrained mitigation actions, measures each hypothetical result by rerunning the same beam equations, records reward, and checkpoints the existing BEAN SHA journal.
- The training cases are **synthetic and bounded**. They are neither structural codes nor verified real CalculiX stress fields. The test harness compares a held-out set against a fixed intervention baseline. It archives raw cases, Q checkpoint, losses and measured results; a zero-gain experiment stays visible.

[Engineering rules/field service test workflow](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-engineering-jobsite.yml)

[Actual BEAN mitigation learning workflow](https://github.com/danieloculus0-bot/BEAN/actions/workflows/bean-engineering-learning.yml)

### Keeping engineering rules trustworthy

Local code requirements differ by location, adopted building-code edition and amendments. Lumber design properties differ by grade, species, product and service conditions. The bundled catalog contains the mathematical rule set but **deliberately leaves jurisdiction-specific allowable spans, connections and strength values unapproved and unset**. Adding a code-backed rule requires identifying the actual source, edition, applicability, material, load combinations, adjustment factors and approval requirements.

The next concrete engineering extensions are: openings/corners/headers in material takeoff; loaded wall and stud stability; multiple supports and nonuniform loads; genuine bolted/welded/contact assembly mechanics in EZ-FEA; and collecting independently verified native FEA/field evidence to train BEAN beyond this elementary beam simulator.

## Commands and boundaries

BEAN's existing `CommandInbox` registers:

- `engineering_jobsite`: versioned `bean.jobsite_request.v1` to perform takeoffs or beam checks.
- `fea_stress_reference`: versioned `bean.stress_request.v1` for the separate circular shaft reference.

Neither inbox command authorizes construction or performs a real CAD FEA solve. The desktop UI runs these same functions through its local HTTP endpoint, not an imitation JavaScript engine.

**Status: working local field-beta calculation and experimental feedback-learning exercise.** Real-world structural reliability needs independent references, verified code values, professional review and native FEA/assembly validation.

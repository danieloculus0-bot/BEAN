# BEAN Spaceflight Reference Lab

Status: **experimental, deterministic analytical solver; not mission software.**
Source: `bean/engineering/spaceflight.py` and `bean/engineering/two_body.py`; tests: `bean/tests/test_spaceflight_reference.py`, `bean/tests/test_two_body_propagation.py`, and `bean/tests/test_spaceflight_inbox.py`.
The hosted BEAN memory plugin is **not** connected to these Python calculations.
On this experimental branch, BEAN Core's actual `bean_run.py` inbox now
registers the `spaceflight_reference` command. No claim is made that BEAN has
autonomously acquired NASA expertise or has supercomputer hardware.

## What runs now

- Earth/Mars/Sun gravitational parameters with JPL provenance, surface-to-orbit gravity,
  escape/circular orbital speeds, circular period and gravitational potential.
- Vis-viva speed for Keplerian orbits and generic two-impulse Hohmann transfer.
- Approximate circular/coplanar Earth-to-Mars heliocentric transfer (about 259 days).
- Ideal rocket fuel mass ratio from specific impulse, dry mass and delta-v.
- Point-mass parking-orbit departure burn to a specified hyperbolic excess speed.
- Simple constant-acceleration time and distance estimates.
- **New:** 3D Newtonian two-body propagation by fixed-step velocity-Verlet, using a
  declared initial state, source-labelled body GM and a physical-radius collision
  guard. Reports energy and angular-momentum drift and the final state. This
  is not date-specific planetary navigation or high-fidelity orbit propagation.
  The result also exposes the initial and final **gravity acceleration vectors**
  in km/s², pointing toward the central body. A test checks the Newtonian
  inverse-square relationship: at twice the radius, gravity is one-quarter as
  strong. These are idealized point-mass accelerations, not measured onboard
  accelerometer readings or a drone guidance command.
- Strict numeric, parameter and operation validation; explicit unit names and method limits.

Use:
```sh
python -m bean.engineering.spaceflight --demo mars
python -m bean.engineering.spaceflight --request '{"schema":"bean.spaceflight_request.v1","calculation":"orbit","parameters":{"body":"mars","altitude_km":400}}'
python -m research.spaceflight.ci_receipt --output spaceflight_receipt.json
python -m unittest bean.tests.test_two_body_propagation -v
```

A two-body propagation request uses the existing strict API:
```json
{
  "schema": "bean.spaceflight_request.v1",
  "calculation": "two_body_propagation",
  "parameters": {
    "body": "earth",
    "position_km": [6771.0084, 0, 0],
    "velocity_km_s": [0, 7.67259, 0],
    "step_seconds": 5,
    "steps": 100
  }
}
```
The state is **assumed** to be body-centered inertial; it is not transformed
from an observed Earth-fixed, spacecraft, or JPL frame. The integrator rejects
steps greater than 5% of the local Keplerian dynamical timescale, invalid
numbers, excessive step counts, and states intersecting the central body's
mean radius. Invariant drift is diagnostic, not a rigorous trajectory error
bound. For a circular Earth orbit, a full revolution and an elliptical
half-revolution are compared against independent analytic predictions; step
refinement is checked separately.

## Spaceflight 101: orbit energy and shape

The two-body result now includes `initial_conic_reference` with **specific
orbital energy**, **eccentricity**, **periapsis**, **apoapsis** (when bound),
and a basic **bound / near-parabolic / unbound** classification.

- **Bound:** total specific energy is negative. An ideal orbit can remain
  gravitationally attached to its central body.
- **Near-parabolic:** specific energy is indistinguishable from zero at the
  declared numerical tolerance. The exact escape boundary is not robustly
  distinguishable in finite precision.
- **Unbound:** specific energy is positive. The ideal trajectory escapes.
- **Periapsis:** closest point implied by the initial position **and velocity
  direction**. The diagnostic flags a predicted periapsis inside the body's
  mean radius, but does not detect all impacts between integration steps.

This is transferable to a robot's general understanding of energy, speed,
momentum and prediction. It does not provide collision-free guidance,
autonomous thruster commands, planetary phasing or safe orbit certification.
The diagnostic is an initial-state *Keplerian snapshot*; the integration
still reports numerical energy/angular-momentum drift independently.

## Native BEAN Core command inbox (experimental)

The existing `bean.runtime.inbox_handlers.register_all` now registers
`spaceflight_reference` in the real `CommandInbox` used by `bean_run.py`.
Use the same `bean.spaceflight_request.v1` JSON object as the CLI, with
`CommandInbox().drop("spaceflight_reference", args=request)` while the
BEAN runtime is running and polling the **same** inbox directory.
The response retains the original physics result and adds
`evidence_receipt.event_id`, `request_sha256` and `result_sha256`.
BEAN's canonical `EventType.OBSERVATION` records the calculation type and
both SHA-256 digests, **not** the raw request or the numeric result. Invalid
requests are quarantined by the existing inbox without a successful
spaceflight observation. The file-based inbox still stores the raw incoming
JSON in its `processed/` or `failed/` folder; do not send secrets there.

The hash receipt proves that a specific calculation input/result pair was
recorded in Core. It does **not** authenticate a source, verify physics
against independent spacecraft observations, update learned weights, or
authorize hardware actions. This handler is not exposed by the hosted
JavaScript BEAN connector. `bean/tests/test_spaceflight_inbox.py` exercises
real registration, queue dispatch, Mars and two-body calculations, hashed
event logging and invalid-input quarantine, with the event writer mocked
so no live DB is modified.

Each CI matrix job writes `spaceflight_receipt.json` with exact source
SHA-256 hashes, GitHub commit/run IDs, test counts, failures and platform
details. Artifacts are retained for 30 days, and the original initial CI
receipt is recorded in `research/spaceflight/verification_ledger.jsonl`.
A receipt can be regenerated locally with the command above. Passing
analytic unit tests does not validate real Mars mission trajectories.

The response schema is `bean.spaceflight_reference.v1` with data provenance,
assumptions and `flight_qualified:false`. It is now wired into the native
Core inbox **on this experimental branch only**, not the hosted BEAN plugin.

## Source provenance and limitations

- [JPL Solar System Dynamics astrodynamic parameters](https://ssd.jpl.nasa.gov/astro_par.html):
  Earth GM 398600.435507 km^3/s^2, Mars-system GM 42828.375816 km^3/s^2,
  Sun GM about 132712440041.2794 km^3/s^2.
- [JPL planetary physical parameters](https://ssd.jpl.nasa.gov/planets/phys_par.html)
  for mean planetary radii.
- [NASA Glenn ideal rocket equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/).
- [JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) and
  [NAIF SPICE](https://naif.jpl.nasa.gov/naif/) are the proposed primary sources
  for precise date-dependent body state vectors; **not connected yet**.

The Mars transfer is a circular-orbit approximation. It cannot select real launch
dates, planetary phasing, atmospheric entry, inclination changes, trajectories
under perturbations, launch vehicle performance, or mission fuel reserves.
Earth-to-Mars heliocentric delta-v values are **not** Earth launch or Mars
capture delta-v requirements.

## Measurable expansion plan

1. **Ephemeris data layer**: ingest Horizons state vectors with explicit UTC/TDB
   convention, center/body IDs, J2000 frame and source snapshot; store hashes.
2. **Trajectory physics**: numerical two-body propagation and conservation tests are
   now implemented; next compare against independent ephemeris data, test more
   eccentric/hyperbolic cases and quantify integration error, then add third-body.
3. **Mission design**: implement/test Lambert transfer and porkchop search with
   recorded departure/arrival epoch, C3, v-infinity and constraints.
4. **Propulsion**: stage sizing and burn windows, electric thrust/integrated mass
   flow, finite acceleration and validated uncertainty budgets.
5. **BEAN reasoning/evidence integration**: native Core inbox and event digests
   are implemented experimentally; future work should connect the existing
   Core evidence ranker, LearningRuntime and compressed ledger without treating
   a successful calculation as independent validation or earned learning reward.
   Separate synthetic reference tests from JPL-held-out comparisons.
6. **Validation**: compare predictions with published JPL/NASA cases and optional
   independent astrodynamics implementation under matched assumptions.
   Keep failed cases; do not infer operational readiness from green unit tests.

Avoid new production dependencies until needed; `spiceypy`, `astropy` and mission
toolkit licensing/accuracy merit a separate audited decision. Test results belong
to the exact branch commit and are not certification or NASA affiliation.

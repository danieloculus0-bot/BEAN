# BEAN Spaceflight Reference Lab

Status: **experimental, deterministic analytical solver; not mission software.**
Source: `bean/engineering/spaceflight.py`; tests: `bean/tests/test_spaceflight_reference.py`.
The BEAN hosted memory plugin is **not** connected to these local Core calculations; this lab
does not claim BEAN has autonomously acquired NASA expertise or has supercomputer hardware.

## What runs now

- Earth/Mars/Sun gravitational parameters with JPL provenance, surface-to-orbit gravity,
  escape/circular orbital speeds, circular period and gravitational potential.
- Vis-viva speed for Keplerian orbits and generic two-impulse Hohmann transfer.
- Approximate circular/coplanar Earth-to-Mars heliocentric transfer (about 259 days).
- Ideal rocket fuel mass ratio from specific impulse, dry mass and delta-v.
- Point-mass parking-orbit departure burn to a specified hyperbolic excess speed.
- Simple constant-acceleration time and distance estimates.
- Strict numeric, parameter and operation validation; explicit unit names and method limits.

Use:
```sh
python -m bean.engineering.spaceflight --demo mars
python -m bean.engineering.spaceflight --request '{"schema":"bean.spaceflight_request.v1","calculation":"orbit","parameters":{"body":"mars","altitude_km":400}}'
python -m unittest bean.tests.test_spaceflight_reference -v
```

The response schema is `bean.spaceflight_reference.v1` with data provenance,
assumptions and `flight_qualified:false`. This is importable by BEAN Python Core
but is **not yet** wired into its native command inbox or hosted BEAN plugin.

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
2. **Trajectory physics**: test numerical two-body propagation for conservation
   of specific energy/angular momentum and analytic Kepler orbits; then third-body.
3. **Mission design**: implement/test Lambert transfer and porkchop search with
   recorded departure/arrival epoch, C3, v-infinity and constraints.
4. **Propulsion**: stage sizing and burn windows, electric thrust/integrated mass
   flow, finite acceleration and validated uncertainty budgets.
5. **BEAN reasoning/evidence integration**: use existing Core evidence ranker,
   LearningRuntime, event journal and compressed ledger; separate synthetic
   reference tests from JPL-held-out comparisons. Include negative tests.
6. **Validation**: compare predictions with published JPL/NASA cases and optional
   independent astrodynamics implementation under matched assumptions.
   Keep failed cases; do not infer operational readiness from green unit tests.

Avoid new production dependencies until needed; `spiceypy`, `astropy` and mission
toolkit licensing/accuracy merit a separate audited decision. Test results belong
to the exact branch commit and are not certification or NASA affiliation.

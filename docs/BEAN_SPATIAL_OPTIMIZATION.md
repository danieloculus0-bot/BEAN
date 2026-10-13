# BEAN Spatial Optimization (experimental 2D planning)

This module computes **candidate layouts** for rooms, factory cells and indoor robot routes. It does not drive machines, certify an installation, or replace a facility survey. Coordinates are dimensioned and deterministic rather than image-generated guesses.

## Run the checks

```bash
python -m pytest bean/tests/test_spatial_optimization.py -q
python -m examples.spatial_factory_demo
```

First local run on 2026-10-13 passed 14 of 14 spatial tests. GitHub Actions separately reruns on Windows/Linux and Python 3.10/3.12. Local green tests do **not** establish that the entire BEAN regression suite has passed.

## Planner model

- Rectangular room, obstacles, and exclusion zones in **one caller-defined unit system**.
- Movable rectangular equipment/furniture, optional 90-degree rotation, permitted zones, and wall buffers.
- Weighted process/material flow. Ranking currently uses center-to-center straight-line distances, **not** measured material-handling routes or travel time.
- Optional required paths between free-space coordinates. Conservative 4-connected A* planning checks simulated robot or vehicle footprints against inflated rectangular obstacles.
- Bounded beam search with deterministic tie-breaking. Lower scores are better. Limited search budgets mean no candidate is **not** proof of impossibility, and the top result is **not guaranteed globally optimal**.
- A result is a 2D geometry hypothesis, **not** a certified forklift aisle, ANSI/RIA robot cell, OSHA egress approval, collision-safe joint trajectory, structural check, or installation drawing.

## Hypothetical factory demonstration

The demo models a 360 x 240 inch rectangular shop cell. Receiving and shipping and a center column stay fixed; a laser and press brake are permitted within their respective zones. Weighted material flow favors receiving, laser, brake, shipping. A simulated radius-8 vehicle footprint must reach from (50,120) to (310,120). These dimensions are illustrative, **not** measurements from a real factory.

First local test's highest-ranked result:

```text
LAYOUT 1: cost=723.76; route=300.32 in; simulation only
  laser: x=85, y=55, w=46, h=35
  press_brake: x=225, y=55, w=45, h=40
```

Do not translate this synthetic footprint into forklift aisle approval. Actual forklift/load envelopes, turn radius, pedestrian segregation, fire routes, machine service access, guarding, utility drops, overhead obstructions, and measured facility boundaries must be supplied and checked separately.

## Apartment application

A 199 x 132 inch room can be represented with a 124 x 86 inch double-chaise sectional, blocked kitchen door-swing zone, and a required patio access path. **Exact** opening geometry and heater-clearance instructions are still required for a final layout. Do not invent rug dimensions.

## Next engineering layers

- CAD/DXF import, polygons, real door-swing envelopes, 3D restrictions, robot reach envelopes.
- Measured material flow, order mix, production volumes, travel time, WIP staging, cell adjacency, utility constraints and one-way lanes.
- Forklift swept turning envelopes, AGV paths, dedicated pedestrian aisles, safety-rated separation and external code validation.
- Supervised motion simulation integrated with existing `bean.motion` safety gates, never bypassing them.
- Sensitivity scenarios for machine downtime, staffing, product mix and growth.

This module is separate from BEAN's self-optimization governor. It does not rewrite software, silently alter process settings or issue actuator commands.

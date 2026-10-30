"""Deterministic spaceflight reference calculations for BEAN.

Idealized two-body / impulsive / constant-acceleration models only.
Not an ephemeris, flight computer, GNC implementation or mission-certified solver.

Source data:
- JPL SSD Astrodynamic Parameters (DE440 planetary GM):
  https://ssd.jpl.nasa.gov/astro_par.html
- JPL Planetary Physical Parameters:
  https://ssd.jpl.nasa.gov/planets/phys_par.html
- NASA Glenn ideal rocket equation:
  https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/
- NASA/JPL Horizons for date-specific ephemerides (NOT implemented here):
  https://ssd-api.jpl.nasa.gov/doc/horizons.html
"""
from __future__ import annotations

import argparse
import json
import math

SCHEMA = "bean.spaceflight_reference.v1"
REQUEST_SCHEMA = "bean.spaceflight_request.v1"
AU_KM = 149597870.7
G0_M_S2 = 9.80665

# JPL SSD planetary-system GM in km^3/s^2; physical mean radius in km.
# Mars uses Mars-system GM rather than a spacecraft-grade Mars-only model.
BODIES = {
    "sun": {"mu_km3_s2": 132712440041.27942, "mean_radius_km": 695700.0},
    "earth": {"mu_km3_s2": 398600.435507, "mean_radius_km": 6371.0084},
    "mars": {"mu_km3_s2": 42828.375816, "mean_radius_km": 3389.5},
}
COMMON_LIMITATIONS = [
    "Simplified analytic reference, not flight-qualified or independently validated",
    "No date-specific ephemeris, perturbations or uncertainty propagation",
    "No finite-burn, gravity/drag loss, atmospheric entry, navigation or operational margins",
]


def _number(value, name, *, minimum=None, strictly_positive=False):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    val = float(value)
    if (minimum is not None and val < minimum) or (strictly_positive and val <= 0):
        raise ValueError(f"{name} is outside its permitted physical range")
    return val


def _body(name):
    if not isinstance(name, str) or name not in BODIES:
        raise ValueError("body must be one of: earth, mars, sun")
    return BODIES[name]


def _params(raw, expected):
    if not isinstance(raw, dict) or set(raw) != set(expected):
        raise ValueError("Parameters must match exactly: " + ", ".join(expected))
    return raw


def orbital_reference(*, body, altitude_km):
    data = _body(body)
    h = _number(altitude_km, "altitude_km", minimum=0)
    r = data["mean_radius_km"] + h
    mu = data["mu_km3_s2"]
    return {
        "body": body, "altitude_km": h, "orbital_radius_km": r,
        "circular_speed_km_s": math.sqrt(mu / r),
        "escape_speed_km_s": math.sqrt(2 * mu / r),
        "circular_period_s": 2 * math.pi * math.sqrt(r**3 / mu),
        "local_gravity_m_s2": 1000 * mu / r**2,
        "specific_gravitational_potential_km2_s2": -mu / r,
    }


def vis_viva_speed(*, mu_km3_s2, radius_km, semimajor_axis_km):
    mu = _number(mu_km3_s2, "mu_km3_s2", strictly_positive=True)
    r = _number(radius_km, "radius_km", strictly_positive=True)
    a = _number(semimajor_axis_km, "semimajor_axis_km", strictly_positive=True)
    v2 = mu * (2 / r - 1 / a)
    if v2 < -1e-10:
        raise ValueError("Requested radius is outside this bound Kepler orbit")
    return math.sqrt(max(0.0, v2))


def hohmann_reference(*, mu_km3_s2, start_radius_km, end_radius_km):
    mu = _number(mu_km3_s2, "mu_km3_s2", strictly_positive=True)
    r1 = _number(start_radius_km, "start_radius_km", strictly_positive=True)
    r2 = _number(end_radius_km, "end_radius_km", strictly_positive=True)
    a = (r1 + r2) / 2
    before = math.sqrt(mu / r1)
    after = math.sqrt(mu / r2)
    transfer_start = math.sqrt(mu * (2 / r1 - 1 / a))
    transfer_end = math.sqrt(mu * (2 / r2 - 1 / a))
    return {
        "start_radius_km": r1, "end_radius_km": r2,
        "transfer_semimajor_axis_km": a,
        "departure_delta_v_km_s": abs(transfer_start - before),
        "arrival_delta_v_km_s": abs(after - transfer_end),
        "total_impulsive_delta_v_km_s": abs(transfer_start - before) + abs(after - transfer_end),
        "transfer_time_days": math.pi * math.sqrt(a**3 / mu) / 86400,
        "assumptions": ["Coplanar circular orbits", "Ideal two-impulse Hohmann transfer"],
    }


def mars_transfer_reference():
    # Approximate mean heliocentric orbit radii, not a launch-date solution.
    estimate = hohmann_reference(
        mu_km3_s2=BODIES["sun"]["mu_km3_s2"],
        start_radius_km=AU_KM,
        end_radius_km=AU_KM * 1.523679,
    )
    estimate["method"] = "circular_coplanar_earth_to_mars_heliocentric_hohmann"
    estimate["earth_orbit_radius_au"] = 1.0
    estimate["mars_orbit_radius_au"] = 1.523679
    estimate["interpretation"] = (
        "Heliocentric velocity changes, NOT launch-to-LEO or Mars-capture fuel "
        "requirements; no actual launch window computed."
    )
    return estimate


def rocket_reference(*, delta_v_km_s, isp_s, dry_mass_kg):
    dv = _number(delta_v_km_s, "delta_v_km_s", minimum=0)
    isp = _number(isp_s, "isp_s", strictly_positive=True)
    dry = _number(dry_mass_kg, "dry_mass_kg", strictly_positive=True)
    exponent = dv * 1000 / (isp * G0_M_S2)
    if exponent > 700:
        raise ValueError("Mass ratio overflows practical numeric range")
    propellant = dry * math.expm1(exponent)
    wet = dry + propellant
    if not all(math.isfinite(x) for x in (propellant, wet)):
        raise ValueError("Computed mass exceeds finite numeric range")
    return {
        "delta_v_km_s": dv, "specific_impulse_s": isp,
        "dry_mass_kg": dry, "propellant_mass_kg": propellant,
        "initial_mass_kg": wet, "mass_ratio": math.exp(exponent),
        "assumptions": ["Ideal rocket equation", "No gravity, drag or steering losses", "Single fixed effective Isp"],
    }


def departure_burn_reference(*, body, parking_altitude_km, v_infinity_km_s):
    orbit = orbital_reference(body=body, altitude_km=parking_altitude_km)
    vinf = _number(v_infinity_km_s, "v_infinity_km_s", minimum=0)
    escape = orbit["escape_speed_km_s"]
    periapsis_speed = math.hypot(vinf, escape)
    return {
        "body": body, "parking_altitude_km": orbit["altitude_km"],
        "hyperbolic_excess_speed_km_s": vinf,
        "circular_parking_speed_km_s": orbit["circular_speed_km_s"],
        "required_impulsive_delta_v_km_s": periapsis_speed - orbit["circular_speed_km_s"],
        "assumptions": ["Impulsive tangential burn at parking-orbit periapsis", "Point-mass two-body dynamics"],
    }


def acceleration_reference(*, delta_v_km_s, acceleration_m_s2):
    dv = _number(delta_v_km_s, "delta_v_km_s", minimum=0) * 1000
    acc = _number(acceleration_m_s2, "acceleration_m_s2", strictly_positive=True)
    time_s = dv / acc
    distance_km = (dv * dv / (2 * acc)) / 1000
    if not all(math.isfinite(x) for x in (time_s, distance_km)):
        raise ValueError("Calculation overflowed")
    return {
        "delta_v_km_s": dv / 1000, "acceleration_m_s2": acc,
        "ideal_acceleration_time_s": time_s,
        "ideal_distance_during_acceleration_km": distance_km,
        "assumptions": ["Constant inertial acceleration from rest", "No external gravity or mass change"],
    }


def two_body_reference(*, body, position_km, velocity_km_s, step_seconds, steps):
    """Propagate a declared initial state using a bounded two-body integrator."""
    from .two_body import propagate_two_body

    data = _body(body)
    result = propagate_two_body(
        mu_km3_s2=data["mu_km3_s2"],
        minimum_radius_km=data["mean_radius_km"],
        position_km=position_km,
        velocity_km_s=velocity_km_s,
        step_seconds=step_seconds,
        steps=steps,
    )
    result["body"] = body
    result["mu_km3_s2"] = data["mu_km3_s2"]
    return result


def solve_spaceflight_reference(request):
    """Solve one declared problem and return an evidence-scoped JSON result.

    Deterministic math is computed here; host BEAN memory / inference / hardware
    are NOT automatically invoked by this function.
    """
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("Unknown spaceflight request schema")
    if set(request) - {"schema", "calculation", "parameters", "source_ref"}:
        raise ValueError("Unknown request fields")
    calc = request.get("calculation")
    p = request.get("parameters")
    if type(calc) is not str:
        raise ValueError("calculation must be a named operation")
    source_ref = request.get("source_ref")
    if source_ref is not None and (not isinstance(source_ref, str) or
                                   not 0 < len(source_ref) <= 200):
        raise ValueError("source_ref must be a bounded nonempty string")
    methods = {
        "orbit": (("body", "altitude_km"), orbital_reference),
        "hohmann": (("mu_km3_s2", "start_radius_km", "end_radius_km"), hohmann_reference),
        "mars_transfer": ((), mars_transfer_reference),
        "rocket": (("delta_v_km_s", "isp_s", "dry_mass_kg"), rocket_reference),
        "departure_burn": (("body", "parking_altitude_km", "v_infinity_km_s"), departure_burn_reference),
        "acceleration": (("delta_v_km_s", "acceleration_m_s2"), acceleration_reference),
        "two_body_propagation": (
            ("body", "position_km", "velocity_km_s", "step_seconds", "steps"),
            two_body_reference,
        ),
    }
    if calc not in methods:
        raise ValueError("Unknown spaceflight calculation")
    fields, fn = methods[calc]
    values = _params(p, fields)
    result = fn(**values)
    return {
        "schema": SCHEMA, "status": "idealized_reference_not_mission_validated",
        "calculation": calc, "source_ref": source_ref, "result": result,
        "limitations": COMMON_LIMITATIONS,
        "data_provenance": {
            "gravitational_parameters": "JPL SSD DE440 astrodynamic parameters",
            "radii": "JPL SSD planetary physical parameters; Sun rounded reference",
            "rocket_equation": "NASA Glenn ideal rocket equation",
            "date_specific_ephemeris": "not_fetched",
        },
        "flight_qualified": False, "physical_hardware_connected": False,
        "independently_validated": False,
    }


def main():
    parser = argparse.ArgumentParser(description="BEAN idealized spaceflight physics reference")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", choices=["mars"])
    group.add_argument("--request", help="JSON object using bean.spaceflight_request.v1")
    args = parser.parse_args()
    request = ({"schema": REQUEST_SCHEMA, "calculation": "mars_transfer", "parameters": {}}
               if args.demo == "mars" else json.loads(args.request))
    print(json.dumps(solve_spaceflight_reference(request), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

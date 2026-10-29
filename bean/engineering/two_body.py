"""Bounded Newtonian two-body state propagation for BEAN's spaceflight lab.

Velocity-Verlet is symplectic for fixed steps in a time-independent central
potential. The method is deterministic, educational and NOT flight-qualified.
No perturbations, thrust, ephemerides, collision model or reference-frame
transformations are provided. All units are km, km/s, km^3/s^2 and seconds.
"""
from __future__ import annotations

import math

SCHEMA = "bean.two_body_propagation.v1"
MAX_STEPS = 20000
MAX_LOCAL_STEP_FRACTION = 0.05


def _real(value, name, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _vector(raw, name):
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise ValueError(f"{name} must be exactly three numeric coordinates")
    return tuple(_real(x, f"{name}[{i}]") for i, x in enumerate(raw))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _norm(vec):
    return math.hypot(*vec)


def _invariants(mu, pos, vel):
    r = _norm(pos)
    energy = 0.5 * _dot(vel, vel) - mu / r
    h = _cross(pos, vel)
    if not all(math.isfinite(x) for x in (energy, *h)):
        raise ValueError("Two-body invariants overflowed")
    return energy, h



def _conic_diagnostics(mu, minimum_radius, pos, vel):
    """Describe the ideal Kepler orbit implied by one inertial state.

    The specific orbital energy determines bound versus escaping motion.
    Eccentricity and periapsis also depend on velocity DIRECTION. These
    osculating values are not collision predictions or maneuver advice.
    """
    radius = _norm(pos)
    energy, h = _invariants(mu, pos, vel)
    v_cross_h = _cross(vel, h)
    e_vec = tuple(x / mu - p / radius for x, p in zip(v_cross_h, pos))
    eccentricity = _norm(e_vec)
    h_mag = _norm(h)
    if not all(math.isfinite(x) for x in (eccentricity, h_mag)):
        raise ValueError("Conic diagnostics overflowed")

    # Finite precision cannot distinguish an exactly parabolic state from
    # a sufficiently close hyperbolic/elliptic state.
    energy_tolerance = 1e-10 * max(mu / radius, 0.5 * _dot(vel, vel), 1e-30)
    if abs(energy) <= energy_tolerance:
        conic = "near_parabolic"
        semimajor = None
    else:
        conic = "bound" if energy < 0 else "unbound"
        semimajor = -mu / (2 * energy)
        if not math.isfinite(semimajor):
            raise ValueError("Semimajor axis overflowed")

    periapsis = (h_mag / math.sqrt(mu))**2 / (1 + eccentricity)
    apoapsis = semimajor * (1 + eccentricity) if conic == "bound" else None
    if not all(math.isfinite(x) for x in (periapsis, *( [apoapsis] if apoapsis is not None else []))):
        raise ValueError("Conic radii overflowed")
    return {
        "classification": conic,
        "specific_orbital_energy_km2_s2": energy,
        "eccentricity": eccentricity,
        "semimajor_axis_km": semimajor,
        "periapsis_radius_km": periapsis,
        "apoapsis_radius_km": apoapsis,
        "periapsis_intersects_body": periapsis <= minimum_radius,
        "degenerate_radial_path": h_mag <= 1e-12 * radius * max(_norm(vel), 1.0),
        "interpretation": (
            "Ideal instantaneous Kepler conic; near_parabolic is numerically "
            "ambiguous, and a periapsis below body radius does not imply a "
            "simulated impact or a safe guidance decision."
        ),
    }


def propagate_two_body(*, mu_km3_s2, minimum_radius_km, position_km,
                       velocity_km_s, step_seconds, steps):
    """Integrate one idealized body-centered inertial state.

    Fixed-step velocity-Verlet. Reject steps above 5% of the local Keplerian
    dynamical timescale sqrt(r^3/mu) and any radius at/below the supplied
    physical-body radius. This is a conservative numeric guard, not a
    general error estimate or collision prediction.
    """
    mu = _real(mu_km3_s2, "mu_km3_s2", positive=True)
    minimum_radius = _real(minimum_radius_km, "minimum_radius_km", positive=True)
    dt = _real(step_seconds, "step_seconds", positive=True)
    if type(steps) is not int or not 1 <= steps <= MAX_STEPS:
        raise ValueError(f"steps must be an integer in 1..{MAX_STEPS}")
    pos = _vector(position_km, "position_km")
    vel = _vector(velocity_km_s, "velocity_km_s")
    elapsed = dt * steps
    if not math.isfinite(elapsed):
        raise ValueError("Propagation duration overflowed")

    def gravity(p):
        radius = _norm(p)
        if not math.isfinite(radius) or radius <= minimum_radius:
            raise ValueError("State intersects the central body or has invalid radius")
        timescale = math.sqrt(radius**3 / mu)
        if not math.isfinite(timescale) or dt > MAX_LOCAL_STEP_FRACTION * timescale:
            raise ValueError("Step exceeds local dynamical timescale limit")
        multiplier = -mu / radius**3
        acceleration = tuple(multiplier * x for x in p)
        if not all(math.isfinite(x) for x in acceleration):
            raise ValueError("Gravitational acceleration overflowed")
        return acceleration

    accel = gravity(pos)
    initial_energy, initial_h = _invariants(mu, pos, vel)
    initial_conic = _conic_diagnostics(mu, minimum_radius, pos, vel)
    initial_radius = _norm(pos)
    energy_scale = max(mu / initial_radius, 0.5 * _dot(vel, vel), 1e-30)
    angular_scale = max(_norm(initial_h), initial_radius * _norm(vel), 1e-30)
    max_energy_drift = 0.0
    max_angular_drift = 0.0
    min_radius = max_radius = initial_radius

    for _ in range(steps):
        next_pos = tuple(p + dt * v + 0.5 * dt * dt * a
                         for p, v, a in zip(pos, vel, accel))
        next_accel = gravity(next_pos)
        next_vel = tuple(v + 0.5 * dt * (a + b)
                         for v, a, b in zip(vel, accel, next_accel))
        if not all(math.isfinite(x) for x in (*next_pos, *next_vel)):
            raise ValueError("Propagated state overflowed")
        pos, vel, accel = next_pos, next_vel, next_accel
        radius = _norm(pos)
        min_radius = min(min_radius, radius)
        max_radius = max(max_radius, radius)
        energy, h = _invariants(mu, pos, vel)
        max_energy_drift = max(max_energy_drift, abs(energy - initial_energy) / energy_scale)
        max_angular_drift = max(max_angular_drift,
                                _norm(tuple(x - y for x, y in zip(h, initial_h))) / angular_scale)

    final_energy, final_h = _invariants(mu, pos, vel)
    return {
        "schema": SCHEMA,
        "method": "fixed_step_velocity_verlet_newtonian_point_mass",
        "frame": "body_centered_inertial_assumed_not_transformed",
        "units": {"position": "km", "velocity": "km/s", "time": "s",
                  "specific_energy": "km^2/s^2", "specific_angular_momentum": "km^2/s"},
        "steps": steps, "step_seconds": dt, "elapsed_seconds": elapsed,
        "final_position_km": list(pos), "final_velocity_km_s": list(vel),
        "initial_conic_reference": initial_conic,
        "initial_specific_energy_km2_s2": initial_energy,
        "final_specific_energy_km2_s2": final_energy,
        "initial_specific_angular_momentum_km2_s": list(initial_h),
        "final_specific_angular_momentum_km2_s": list(final_h),
        "max_scaled_specific_energy_drift": max_energy_drift,
        "max_scaled_angular_momentum_vector_drift": max_angular_drift,
        "min_radius_km": min_radius, "max_radius_km": max_radius,
        "physical_body_radius_km": minimum_radius,
        "status": "idealized_numerical_reference_not_mission_validated",
        "assumptions": [
            "Newtonian central point-mass gravity with constant mu",
            "User-supplied body-centered inertial state and fixed time step",
            "No J2, third bodies, relativity, atmosphere, burns or date-specific ephemerides",
            "Conic classification is a snapshot from the initial state, not a navigation solution",
            "Step guard and invariant drift are diagnostics, not error bounds",
        ],
        "flight_qualified": False,
    }

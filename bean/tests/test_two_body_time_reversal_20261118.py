"""Seeded time-reversal challenge for the existing Newtonian two-body solver.

This tests a symmetry of the equations independently of the solver's own
reported conservation diagnostics. It does not measure BEAN learning.
"""
import math
import random

import pytest

from bean.engineering.two_body import propagate_two_body


@pytest.mark.parametrize("seed", range(12))
def test_velocity_verlet_reverses_unseen_inertial_states(seed):
    rng = random.Random(20261118 + seed)
    radius = rng.uniform(6900.0, 18000.0)
    angle = rng.uniform(-math.pi, math.pi)
    tilt = rng.uniform(-0.35, 0.35)
    position = [radius * math.cos(angle), radius * math.sin(angle), 0.0]
    circular_speed = math.sqrt(398600.435507 / radius)
    speed = circular_speed * rng.uniform(0.80, 1.12)
    velocity = [
        -speed * math.sin(angle) * math.cos(tilt),
        speed * math.cos(angle) * math.cos(tilt),
        speed * math.sin(tilt),
    ]
    params = {"mu_km3_s2": 398600.435507, "minimum_radius_km": 6371.0084,
              "step_seconds": 2.0, "steps": 120}
    forward = propagate_two_body(position_km=position, velocity_km_s=velocity, **params)
    backward = propagate_two_body(
        position_km=forward["final_position_km"],
        velocity_km_s=[-v for v in forward["final_velocity_km_s"]],
        **params,
    )
    # Reverse the final velocity again to compare in the original time direction.
    position_residual = math.dist(position, backward["final_position_km"])
    velocity_residual = math.dist(
        velocity, [-v for v in backward["final_velocity_km_s"]]
    )
    assert position_residual < 1e-7, (seed, position_residual)
    assert velocity_residual < 1e-10, (seed, velocity_residual)
    assert forward["max_scaled_specific_energy_drift"] < 1e-5
    assert backward["max_scaled_angular_momentum_vector_drift"] < 1e-10


def test_reversal_control_detects_missing_velocity_sign_flip():
    params = {"mu_km3_s2": 398600.435507, "minimum_radius_km": 6371.0084,
              "step_seconds": 2.0, "steps": 120}
    p = [9000.0, 0.0, 0.0]
    v = [0.0, 6.5, 0.3]
    forward = propagate_two_body(position_km=p, velocity_km_s=v, **params)
    # A forward continuation is not a time reversal: negative control.
    control = propagate_two_body(
        position_km=forward["final_position_km"],
        velocity_km_s=forward["final_velocity_km_s"], **params
    )
    assert math.dist(p, control["final_position_km"]) > 100.0

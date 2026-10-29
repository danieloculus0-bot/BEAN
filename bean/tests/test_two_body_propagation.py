"""Independent physical-invariant checks for BEAN's bounded two-body integrator."""
import math
import unittest

from bean.engineering.spaceflight import BODIES, REQUEST_SCHEMA, solve_spaceflight_reference
from bean.engineering.two_body import MAX_STEPS, propagate_two_body


MU = BODIES["earth"]["mu_km3_s2"]
EARTH_RADIUS = BODIES["earth"]["mean_radius_km"]


def reference(*, radius=7000., velocity=None, dt=5., steps=100):
    if velocity is None:
        velocity = math.sqrt(MU / radius)
    return propagate_two_body(
        mu_km3_s2=MU, minimum_radius_km=EARTH_RADIUS,
        position_km=[radius, 0., 0.], velocity_km_s=[0., velocity, 0.],
        step_seconds=dt, steps=steps,
    )


class TestTwoBodyPropagation(unittest.TestCase):
    def test_circular_one_period_and_conservation(self):
        radius = EARTH_RADIUS + 400
        speed = math.sqrt(MU / radius)
        period = 2 * math.pi * math.sqrt(radius**3 / MU)
        out = reference(radius=radius, velocity=speed, dt=period/1000, steps=1000)
        self.assertAlmostEqual(out["final_position_km"][0], radius, delta=1.0)
        self.assertAlmostEqual(out["final_position_km"][1], 0, delta=1.0)
        self.assertAlmostEqual(out["final_velocity_km_s"][1], speed, delta=0.002)
        self.assertLess(out["max_scaled_specific_energy_drift"], 1e-7)
        self.assertLess(out["max_scaled_angular_momentum_vector_drift"], 1e-10)
        self.assertFalse(out["flight_qualified"])

    def test_elliptical_half_period_apoapsis_and_angular_momentum(self):
        periapsis, apoapsis = 7000., 14000.
        semimajor = (periapsis + apoapsis) / 2
        periapsis_speed = math.sqrt(MU * (2/periapsis - 1/semimajor))
        period = 2 * math.pi * math.sqrt(semimajor**3 / MU)
        out = reference(radius=periapsis, velocity=periapsis_speed,
                        dt=period/2000, steps=1000)
        self.assertAlmostEqual(out["final_position_km"][0], -apoapsis, delta=1.0)
        self.assertAlmostEqual(out["final_position_km"][1], 0, delta=1.0)
        self.assertAlmostEqual(out["final_velocity_km_s"][1],
                               -periapsis_speed * periapsis/apoapsis, delta=0.001)
        self.assertLess(out["max_scaled_specific_energy_drift"], 1e-5)
        self.assertLess(out["max_scaled_angular_momentum_vector_drift"], 1e-10)

    def test_step_refinement_reduces_closed_orbit_phase_error(self):
        radius = EARTH_RADIUS + 400
        period = 2 * math.pi * math.sqrt(radius**3 / MU)
        coarse = reference(radius=radius, dt=period/250, steps=250)
        fine = reference(radius=radius, dt=period/1000, steps=1000)
        coarse_error = math.dist(coarse["final_position_km"], [radius, 0., 0.])
        fine_error = math.dist(fine["final_position_km"], [radius, 0., 0.])
        self.assertGreater(coarse_error, 1.0)
        self.assertLess(fine_error, coarse_error/10)

    def test_schema_route_and_metadata(self):
        radius = EARTH_RADIUS + 400
        speed = math.sqrt(MU / radius)
        out = solve_spaceflight_reference({
            "schema": REQUEST_SCHEMA, "calculation": "two_body_propagation",
            "parameters": {
                "body": "earth", "position_km": [radius, 0, 0],
                "velocity_km_s": [0, speed, 0], "step_seconds": 5, "steps": 20,
            }, "source_ref": "analytic-invariant-test",
        })
        self.assertEqual(out["result"]["body"], "earth")
        self.assertEqual(out["result"]["steps"], 20)
        self.assertEqual(out["result"]["frame"],
                         "body_centered_inertial_assumed_not_transformed")
        self.assertEqual(out["source_ref"], "analytic-invariant-test")
        self.assertFalse(out["flight_qualified"])
        self.assertFalse(out["independently_validated"])

    def test_rejects_invalid_states_and_collision(self):
        valid = {
            "mu_km3_s2": MU, "minimum_radius_km": EARTH_RADIUS,
            "position_km": [7000., 0., 0.], "velocity_km_s": [0., 7.5, 0.],
            "step_seconds": 5., "steps": 10,
        }
        changes = [
            {"mu_km3_s2": -1},
            {"mu_km3_s2": float("nan")},
            {"minimum_radius_km": 0},
            {"position_km": [EARTH_RADIUS, 0, 0]},
            {"position_km": [0, 0, 0]},
            {"position_km": [7000, 0]},
            {"position_km": [7000, 0, float("inf")]},
            {"velocity_km_s": [0, True, 0]},
            {"step_seconds": 0},
            {"step_seconds": 1000},
            {"steps": 0},
            {"steps": MAX_STEPS + 1},
            {"steps": 10.0},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                propagate_two_body(**{**valid, **change})
        with self.assertRaises(ValueError):
            propagate_two_body(**{**valid, "position_km": [EARTH_RADIUS+1, 0, 0],
                                  "velocity_km_s": [0, 0, 0], "step_seconds": 1.,
                                  "steps": 200})
        with self.assertRaises(ValueError):
            solve_spaceflight_reference({
                "schema": REQUEST_SCHEMA, "calculation": "two_body_propagation",
                "parameters": {"body": "earth", "position_km": [7000, 0, 0],
                               "velocity_km_s": [0, 7.5, 0], "step_seconds": 5,
                               "steps": 5, "unknown": "not allowed"},
            })


if __name__ == "__main__":
    unittest.main()

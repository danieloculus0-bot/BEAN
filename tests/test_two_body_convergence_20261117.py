"""Seeded circular-orbit convergence checks against independent Kepler periods.

This verifies the deterministic two-body reference, NOT BEAN learning or
autonomous solver selection. SI-compatible km, km/s and seconds throughout.
"""
import math
import random
import unittest

from bean.engineering.two_body import propagate_two_body

MU = 398600.435507  # km^3/s^2, same declared JPL Earth GM as spaceflight.py
EARTH_RADIUS = 6371.0084  # km
SEED = 20261117


class TwoBodyConvergence(unittest.TestCase):
    def test_seeded_rotated_circular_orbits_converge_quadratically(self):
        rng = random.Random(SEED)
        for case in range(4):
            altitude = rng.uniform(350.0, 1500.0)
            phase = rng.uniform(-math.pi, math.pi)
            inclination = rng.uniform(0.1, 1.3)
            radius = EARTH_RADIUS + altitude
            speed = math.sqrt(MU / radius)
            period = 2 * math.pi * math.sqrt(radius ** 3 / MU)
            # Rotate an inertial circular orbit in both phase and inclination.
            radial = (math.cos(phase), math.sin(phase) * math.cos(inclination),
                      math.sin(phase) * math.sin(inclination))
            tangent = (-math.sin(phase), math.cos(phase) * math.cos(inclination),
                       math.cos(phase) * math.sin(inclination))
            initial_position = [radius * x for x in radial]
            initial_velocity = [speed * x for x in tangent]

            errors = []
            for steps in (400, 800):
                result = propagate_two_body(
                    mu_km3_s2=MU,
                    minimum_radius_km=EARTH_RADIUS,
                    position_km=initial_position,
                    velocity_km_s=initial_velocity,
                    step_seconds=period / steps,
                    steps=steps,
                )
                error = math.dist(result["final_position_km"], initial_position)
                errors.append(error)
                with self.subTest(case=case, steps=steps):
                    self.assertEqual(result["steps"], steps)
                    self.assertAlmostEqual(result["elapsed_seconds"], period, delta=1e-8)
                    self.assertLess(result["max_scaled_specific_energy_drift"], 1e-6)
                    self.assertLess(result["max_scaled_angular_momentum_vector_drift"], 1e-10)
                    self.assertFalse(result["initial_conic_reference"]["periapsis_intersects_body"])
                    self.assertEqual(result["initial_conic_reference"]["classification"], "bound")

            with self.subTest(case=case, convergence="position"):
                # Velocity-Verlet has second-order global position error.
                # An analytic Kepler period is the independent oracle here.
                self.assertGreater(errors[0], 0.1)
                self.assertLess(errors[1], 2.0)
                self.assertGreater(errors[0] / errors[1], 3.7)

    def test_rejects_body_intersection_and_oversized_step(self):
        with self.assertRaises(ValueError):
            propagate_two_body(
                mu_km3_s2=MU, minimum_radius_km=EARTH_RADIUS,
                position_km=[EARTH_RADIUS, 0, 0],
                velocity_km_s=[0, 8, 0], step_seconds=1, steps=1)
        with self.assertRaises(ValueError):
            propagate_two_body(
                mu_km3_s2=MU, minimum_radius_km=EARTH_RADIUS,
                position_km=[7000, 0, 0], velocity_km_s=[0, 7.5, 0],
                step_seconds=1000, steps=1)


if __name__ == "__main__":
    unittest.main()

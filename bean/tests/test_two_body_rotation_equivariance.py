"""Seeded rotation-equivariance acceptance for the existing two-body integrator.

Independent geometric metamorphic test, not evidence of cognitive learning.
All coordinates are body-centered inertial km and km/s. A 90-degree proper
rotation about z must commute with isotropic Newtonian propagation.
"""
import math
import random
import unittest

from bean.engineering.two_body import propagate_two_body


def rotate_z90(v):
    return [-v[1], v[0], v[2]]


class TwoBodyRotationEquivariance(unittest.TestCase):
    def test_seeded_three_dimensional_rotation_equivariance(self):
        rng = random.Random(20261118)
        mu = 398600.4418  # public synthetic Earth-like gravitational parameter
        for case in range(12):
            # Perturb a stable inclined orbit; avoid surface intersections.
            radius = rng.uniform(8000.0, 15000.0)
            position = [radius, 0.0, rng.uniform(-300.0, 300.0)]
            circular_speed = math.sqrt(mu / radius)
            velocity = [
                rng.uniform(-0.3, 0.3),
                circular_speed * rng.uniform(0.9, 1.05),
                rng.uniform(-0.6, 0.6),
            ]
            params = dict(mu_km3_s2=mu, minimum_radius_km=6000.0,
                          step_seconds=2.0, steps=500)
            original = propagate_two_body(position_km=position,
                                          velocity_km_s=velocity, **params)
            rotated = propagate_two_body(position_km=rotate_z90(position),
                                         velocity_km_s=rotate_z90(velocity), **params)
            with self.subTest(case=case):
                for key in ("final_position_km", "final_velocity_km_s",
                            "final_gravitational_acceleration_km_s2",
                            "initial_specific_angular_momentum_km2_s",
                            "final_specific_angular_momentum_km2_s"):
                    expected = rotate_z90(original[key])
                    actual = rotated[key]
                    for a, b in zip(actual, expected):
                        self.assertTrue(math.isclose(a, b, rel_tol=2e-11,
                                                      abs_tol=2e-9),
                                        msg=f"{key}: {actual} != {expected}")
                for key in ("initial_specific_energy_km2_s2",
                            "final_specific_energy_km2_s2",
                            "min_radius_km", "max_radius_km"):
                    self.assertTrue(math.isclose(original[key], rotated[key],
                                                  rel_tol=2e-11, abs_tol=2e-9))
                self.assertEqual(original["initial_conic_reference"]["classification"],
                                 rotated["initial_conic_reference"]["classification"])


if __name__ == "__main__":
    unittest.main()

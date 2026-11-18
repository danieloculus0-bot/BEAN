"""Metamorphic physics acceptance: dimensional similarity of linear-drag flight.

Independent from the solver's closed-form trajectory. Fixed synthetic inputs.
This verifies reference mathematics, not native BEAN learning or autonomy.
"""
import math
import random
import unittest

from bean.engineering.earth_projectile import solve_earth_projectile


class ProjectileDimensionalSimilarity(unittest.TestCase):
    def test_time_rescaling_preserves_dimensionless_trajectory(self):
        # Under t' = t / c, v' = c*v, g' = c*c*g, k' = c*k,
        # the x/y trajectory and drag work per unit mass / c^2 are invariant.
        rng = random.Random(20261118)
        for index in range(24):
            speed = rng.uniform(8.0, 75.0)
            angle = rng.uniform(-20.0, 80.0)
            height = rng.uniform(1.0, 40.0)
            gravity = rng.uniform(3.0, 15.0)
            drag = rng.uniform(0.005, 0.6)
            scale = rng.uniform(0.3, 3.0)
            def run(v, g, k):
                return solve_earth_projectile(
                    launch_speed_m_s=v, angle_deg=angle,
                    initial_height_m=height, gravity_m_s2=g,
                    linear_drag_s_inv=k)
            base = run(speed, gravity, drag)
            scaled = run(speed*scale, gravity*scale**2, drag*scale)
            with self.subTest(case=index):
                self.assertTrue(math.isclose(
                    base["horizontal_range_m"], scaled["horizontal_range_m"],
                    rel_tol=2e-10, abs_tol=1e-8))
                self.assertTrue(math.isclose(
                    base["peak_height_m"], scaled["peak_height_m"],
                    rel_tol=2e-10, abs_tol=1e-8))
                self.assertTrue(math.isclose(
                    base["flight_time_s"], scaled["flight_time_s"]*scale,
                    rel_tol=2e-10, abs_tol=1e-8))
                self.assertTrue(math.isclose(
                    base["peak_time_s"], scaled["peak_time_s"]*scale,
                    rel_tol=2e-10, abs_tol=1e-8))
                for original, transformed in zip(
                        base["impact_velocity_m_s"], scaled["impact_velocity_m_s"]):
                    self.assertTrue(math.isclose(
                        original, transformed/scale,
                        rel_tol=2e-10, abs_tol=1e-8))
                self.assertTrue(math.isclose(
                    base["specific_mechanical_energy_loss_m2_s2"],
                    scaled["specific_mechanical_energy_loss_m2_s2"]/scale**2,
                    rel_tol=2e-9, abs_tol=1e-7))


if __name__ == "__main__":
    unittest.main()

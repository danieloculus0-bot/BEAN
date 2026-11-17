"""Independent analytical acceptance cases for terrestrial projectile mechanics."""
import math
import unittest

from bean.engineering.earth_projectile import solve_earth_projectile


def solve(speed=20., angle=30., h=0., g=9.81, k=0.):
    return solve_earth_projectile(launch_speed_m_s=speed, angle_deg=angle,
                                  initial_height_m=h, gravity_m_s2=g,
                                  linear_drag_s_inv=k)


class EarthProjectileTests(unittest.TestCase):
    def test_vacuum_launch_matches_independent_parabola(self):
        a = math.radians(30)
        t = 2 * 20 * math.sin(a) / 9.81
        out = solve()
        self.assertAlmostEqual(out["flight_time_s"], t, places=9)
        self.assertAlmostEqual(out["horizontal_range_m"], 20 * math.cos(a) * t, places=8)
        self.assertAlmostEqual(out["peak_height_m"], (20*math.sin(a))**2 / (2*9.81), places=8)
        self.assertAlmostEqual(out["specific_mechanical_energy_loss_m2_s2"], 0, delta=1e-8)

    def test_elevated_vertical_drop(self):
        out = solve(speed=0, h=45)
        self.assertAlmostEqual(out["flight_time_s"], math.sqrt(90/9.81), places=9)
        self.assertAlmostEqual(out["horizontal_range_m"], 0, places=9)
        self.assertAlmostEqual(out["impact_velocity_m_s"][1], -math.sqrt(90*9.81), places=8)

    def test_drag_reduces_range_and_energy(self):
        vacuum, drag = solve(), solve(k=.3)
        self.assertLess(drag["horizontal_range_m"], vacuum["horizontal_range_m"])
        self.assertLess(drag["peak_height_m"], vacuum["peak_height_m"])
        self.assertGreater(drag["specific_mechanical_energy_loss_m2_s2"], 0)
        self.assertLess(drag["flight_time_s"], vacuum["flight_time_s"])

    def test_near_vacuum_limit_is_numerically_stable(self):
        near = solve(k=1e-11)
        vacuum = solve()
        self.assertAlmostEqual(near["flight_time_s"], vacuum["flight_time_s"], delta=1e-8)
        self.assertAlmostEqual(near["horizontal_range_m"], vacuum["horizontal_range_m"], delta=1e-8)

    def test_surface_launch_with_nonupward_velocity_is_immediate(self):
        out = solve(speed=40, angle=0)
        self.assertEqual(out["flight_time_s"], 0)
        self.assertEqual(out["horizontal_range_m"], 0)

    def test_invalid_physical_inputs_rejected(self):
        for kwargs in ({"g":0}, {"h":-1}, {"speed":-1}, {"k":-1},
                       {"k":float("nan")}, {"angle":120}, {"speed":True},
                       {"h":1e9}, {"k":1e9}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                solve(**kwargs)

    def test_overlong_drag_case_fails_closed(self):
        with self.assertRaises(ValueError):
            solve(speed=0, h=1e7, k=1e6)


if __name__ == "__main__":
    unittest.main()

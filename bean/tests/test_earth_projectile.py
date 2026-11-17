"""Independent analytical acceptance cases for terrestrial projectile mechanics."""
import math
import unittest

from bean.engineering.earth_projectile import solve_earth_projectile
from bean.engineering.spaceflight import REQUEST_SCHEMA, solve_spaceflight_reference


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

    def test_native_spaceflight_request_dispatch(self):
        from bean.engineering.spaceflight import REQUEST_SCHEMA, solve_spaceflight_reference
        request = {
            "schema": REQUEST_SCHEMA, "calculation": "earth_projectile",
            "parameters": {
                "launch_speed_m_s": 20, "angle_deg": 30,
                "initial_height_m": 0, "gravity_m_s2": 9.81,
                "linear_drag_s_inv": 0,
            },
        }
        response = solve_spaceflight_reference(request)
        self.assertEqual(response["result"]["schema"], "bean.earth_projectile_reference.v1")
        self.assertAlmostEqual(response["result"]["horizontal_range_m"],
                               solve()["horizontal_range_m"], places=9)
        self.assertFalse(response["flight_qualified"])
        with self.assertRaises(ValueError):
            solve_spaceflight_reference({**request, "parameters":
                {**request["parameters"], "unexpected": 1}})

    def test_invalid_physical_inputs_rejected(self):
        for kwargs in ({"g":0}, {"h":-1}, {"speed":-1}, {"k":-1},
                       {"k":float("nan")}, {"angle":120}, {"speed":True},
                       {"h":1e9}, {"k":1e9}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                solve(**kwargs)

    def test_existing_bean_physics_dispatcher(self):
        request = {"schema":REQUEST_SCHEMA, "calculation":"earth_projectile",
                   "parameters":{
                       "launch_speed_m_s":20, "angle_deg":30,
                       "initial_height_m":0, "gravity_m_s2":9.81,
                       "linear_drag_s_inv":0.3,
                   }}
        out = solve_spaceflight_reference(request)
        self.assertEqual(out["calculation"], "earth_projectile")
        self.assertEqual(out["result"]["schema"], "bean.earth_projectile_reference.v1")
        self.assertGreater(out["result"]["horizontal_range_m"], 0)
        self.assertFalse(out["flight_qualified"])
        self.assertFalse(out["independently_validated"])
        self.assertEqual(out["data_provenance"]["earth_projectile_gravity"],
                         "caller_supplied_constant_not_measured")
        with self.assertRaises(ValueError):
            solve_spaceflight_reference({**request, "parameters":
                {**request["parameters"], "extra":1}})

    def test_overlong_drag_case_fails_closed(self):
        with self.assertRaises(ValueError):
            solve(speed=0, h=1e7, k=1e6)


    def test_seeded_unseen_linear_drag_against_independent_rk4(self):
        """12 deterministic synthetic cases; independent ODE integration, not Core learning.

        Fixed seed 20261117; 12 cases, dt=0.002 s, no model feedback or
        parameter fitting. Impact is interpolated between RK4 steps.
        Checks solver correctness only; not autonomous task selection.
        """
        import random
        rng = random.Random(20261117)
        for case in range(12):
            speed = rng.uniform(12.0, 90.0)
            angle = rng.uniform(12.0, 78.0)
            height = rng.uniform(2.0, 35.0)
            gravity = rng.uniform(3.0, 15.0)
            drag = rng.uniform(0.015, 0.45)
            exact = solve(speed=speed, angle=angle, h=height, g=gravity, k=drag)
            theta = math.radians(angle)
            state = (0.0, height, speed * math.cos(theta), speed * math.sin(theta))
            dt = 0.002

            def derivative(s):
                x, y, vx, vy = s
                return (vx, vy, -drag * vx, -gravity - drag * vy)

            def advance(s):
                k1 = derivative(s)
                k2 = derivative(tuple(v + 0.5 * dt * d for v, d in zip(s, k1)))
                k3 = derivative(tuple(v + 0.5 * dt * d for v, d in zip(s, k2)))
                k4 = derivative(tuple(v + dt * d for v, d in zip(s, k3)))
                return tuple(v + dt * (a + 2*b + 2*c + d) / 6
                             for v, a, b, c, d in zip(s, k1, k2, k3, k4))

            elapsed = 0.0
            for step in range(100000):
                previous = state
                state = advance(state)
                elapsed += dt
                if state[1] <= 0:
                    fraction = previous[1] / (previous[1] - state[1])
                    impact_x = previous[0] + fraction * (state[0] - previous[0])
                    impact_t = elapsed - dt + fraction * dt
                    with self.subTest(case=case, speed=speed, drag=drag):
                        self.assertAlmostEqual(exact["flight_time_s"], impact_t, delta=0.003)
                        self.assertAlmostEqual(exact["horizontal_range_m"], impact_x, delta=0.03)
                        self.assertGreaterEqual(exact["specific_mechanical_energy_loss_m2_s2"], 0)
                    break
            else:
                self.fail(f"Seeded RK4 case {case} did not impact within 200 seconds")



if __name__ == "__main__":
    unittest.main()

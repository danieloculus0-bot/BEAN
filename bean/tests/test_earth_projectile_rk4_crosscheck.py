"""Independent fixed-step RK4 crosscheck of BEAN's closed-form drag reference.

These seeded synthetic inputs are not a learned-solver benchmark.  The RK4
equations are implemented separately from the production analytic formula.
"""
import math
import random
import unittest

from bean.engineering.earth_projectile import solve_earth_projectile


def rk4_trajectory(speed, angle, height, gravity, drag, duration, steps=12000):
    theta = math.radians(angle)
    state = (0.0, height, speed * math.cos(theta), speed * math.sin(theta))
    dt = duration / steps

    def derivative(s):
        return (s[2], s[3], -drag * s[2], -gravity - drag * s[3])

    def advance(s, d, factor):
        return tuple(a + factor * b for a, b in zip(s, d))

    for _ in range(steps):
        k1 = derivative(state)
        k2 = derivative(advance(state, k1, dt / 2))
        k3 = derivative(advance(state, k2, dt / 2))
        k4 = derivative(advance(state, k3, dt))
        state = tuple(
            s + dt * (a + 2*b + 2*c + d) / 6
            for s, a, b, c, d in zip(state, k1, k2, k3, k4)
        )
    return state


class EarthProjectileIndependentNumerics(unittest.TestCase):
    def test_seeded_withheld_parameter_crosscheck(self):
        rng = random.Random(20261118)
        for case in range(12):
            speed = rng.uniform(4, 85)
            angle = rng.uniform(-55, 85)
            height = rng.uniform(2, 90)
            gravity = rng.uniform(3, 18)
            drag = rng.uniform(0.001, 0.8)
            output = solve_earth_projectile(
                launch_speed_m_s=speed, angle_deg=angle,
                initial_height_m=height, gravity_m_s2=gravity,
                linear_drag_s_inv=drag,
            )
            t = output["flight_time_s"]
            x, y, vx, vy = rk4_trajectory(
                speed, angle, height, gravity, drag, t,
            )
            with self.subTest(case=case, seed=20261118):
                self.assertAlmostEqual(y, 0, delta=2e-7)
                self.assertAlmostEqual(x, output["horizontal_range_m"], delta=2e-6)
                self.assertAlmostEqual(vx, output["impact_velocity_m_s"][0], delta=2e-7)
                self.assertAlmostEqual(vy, output["impact_velocity_m_s"][1], delta=2e-7)
                loss = speed**2 / 2 + gravity * height - (vx**2 + vy**2) / 2
                self.assertAlmostEqual(
                    loss, output["specific_mechanical_energy_loss_m2_s2"],
                    delta=2e-5,
                )
                self.assertGreaterEqual(loss, -2e-7)

    def test_zero_drag_independent_limit(self):
        speed, angle, height, gravity = 29.0, -18.0, 21.0, 9.81
        result = solve_earth_projectile(
            launch_speed_m_s=speed, angle_deg=angle,
            initial_height_m=height, gravity_m_s2=gravity,
            linear_drag_s_inv=0.0,
        )
        vx0 = speed * math.cos(math.radians(angle))
        vy0 = speed * math.sin(math.radians(angle))
        t = (vy0 + math.sqrt(vy0**2 + 2 * gravity * height)) / gravity
        self.assertAlmostEqual(result["flight_time_s"], t, delta=1e-9)
        self.assertAlmostEqual(result["horizontal_range_m"], vx0 * t, delta=1e-8)
        self.assertAlmostEqual(result["specific_mechanical_energy_loss_m2_s2"], 0, delta=1e-8)


if __name__ == "__main__":
    unittest.main()

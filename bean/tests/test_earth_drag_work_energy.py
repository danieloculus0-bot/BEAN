"""Independent work-energy crosschecks for the existing Earth projectile reference.

The numeric control integrates x,y,vx,vy and drag work with RK4, independently
of the closed-form solver. This tests physics correctness, not BEAN learning.
"""
import math
import unittest

from bean.engineering.earth_projectile import solve_earth_projectile


class DragWorkEnergyCrosscheck(unittest.TestCase):
    def test_seeded_drag_work_matches_mechanical_energy_loss(self):
        import random
        rng = random.Random(20261119)
        for case in range(8):
            speed = rng.uniform(14.0, 55.0)
            angle = rng.uniform(15.0, 70.0)
            height = rng.uniform(3.0, 25.0)
            gravity = rng.uniform(4.0, 14.0)
            drag = rng.uniform(0.04, 0.4)
            result = solve_earth_projectile(
                launch_speed_m_s=speed, angle_deg=angle,
                initial_height_m=height, gravity_m_s2=gravity,
                linear_drag_s_inv=drag,
            )
            theta = math.radians(angle)
            # State: horizontal position, vertical position, velocity x/y,
            # cumulative specific drag work (positive dissipation).
            state = (0.0, height, speed * math.cos(theta),
                     speed * math.sin(theta), 0.0)
            dt = 0.001

            def deriv(s):
                _, _, vx, vy, _ = s
                return (vx, vy, -drag * vx, -gravity - drag * vy,
                        drag * (vx * vx + vy * vy))

            def advance(s, h):
                a = deriv(s)
                b = deriv(tuple(q + h * p / 2 for q, p in zip(s, a)))
                c = deriv(tuple(q + h * p / 2 for q, p in zip(s, b)))
                d = deriv(tuple(q + h * p for q, p in zip(s, c)))
                return tuple(q + h * (u + 2*v + 2*w + z)/6
                             for q, u, v, w, z in zip(s, a, b, c, d))

            # Integrate to the independently computed impact time, avoiding
            # interpolated energy at a step that has already crossed ground.
            remaining = result["flight_time_s"]
            for _ in range(100000):
                if remaining <= 0:
                    break
                h = min(dt, remaining)
                state = advance(state, h)
                remaining -= h
                if remaining < 1e-12:
                    break
            else:
                self.fail("Numerical integration exceeded fixed budget")
            initial_energy = 0.5 * speed**2 + gravity * height
            final_energy = 0.5 * (state[2]**2 + state[3]**2) + gravity * state[1]
            with self.subTest(case=case):
                self.assertAlmostEqual(state[1], 0.0, delta=2e-6)
                self.assertAlmostEqual(
                    result["specific_mechanical_energy_loss_m2_s2"],
                    state[4], delta=2e-5,
                )
                self.assertAlmostEqual(
                    initial_energy - final_energy, state[4], delta=2e-5,
                )
                self.assertGreaterEqual(state[4], 0.0)


if __name__ == "__main__":
    unittest.main()

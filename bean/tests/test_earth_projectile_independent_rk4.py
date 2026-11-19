"""Independent numerical crosschecks for BEAN's Earth projectile reference.

The oracle integrates the differential equations with RK4 rather than
reusing the solver's exponential closed form or its impact root finder.
This tests reference-tool correctness, NOT autonomous learning.
"""
import math
import unittest

from bean.engineering.earth_projectile import solve_earth_projectile


def rk4_at_time(speed, angle_deg, height, gravity, drag, duration, steps):
    radians = math.radians(angle_deg)
    state = (0.0, height, speed * math.cos(radians),
             speed * math.sin(radians))
    dt = duration / steps

    def derivative(s):
        _, _, vx, vy = s
        return (vx, vy, -drag * vx, -gravity - drag * vy)

    def add(s, k, scale):
        return tuple(a + scale * b for a, b in zip(s, k))

    for _ in range(steps):
        k1 = derivative(state)
        k2 = derivative(add(state, k1, dt / 2))
        k3 = derivative(add(state, k2, dt / 2))
        k4 = derivative(add(state, k3, dt))
        state = tuple(a + dt * (b + 2*c + 2*d + e) / 6
                      for a, b, c, d, e in zip(state, k1, k2, k3, k4))
    return state


class IndependentProjectileCheck(unittest.TestCase):
    def test_held_out_numerical_crosschecks(self):
        # Synthetic parameter sets, including descending launch, zero drag,
        # and near-zero drag to exercise cancellation-sensitive expressions.
        cases = (
            (43.7, 37.2, 8.3, 9.81, 0.041),
            (21.4, -18.5, 30.0, 9.77, 0.0),
            (105.3, 64.1, 2.5, 9.83, 1e-8),
        )
        for speed, angle, height, gravity, drag in cases:
            with self.subTest(case=(speed, angle, height, gravity, drag)):
                reference = solve_earth_projectile(
                    launch_speed_m_s=speed, angle_deg=angle,
                    initial_height_m=height, gravity_m_s2=gravity,
                    linear_drag_s_inv=drag)
                flight = reference["flight_time_s"]
                coarse = rk4_at_time(speed, angle, height, gravity, drag,
                                     flight, 100)
                fine = rk4_at_time(speed, angle, height, gravity, drag,
                                   flight, 200)
                # Independent integration must converge toward the analytic
                # trajectory as its step size halves.
                expected = (reference["horizontal_range_m"], 0.0,
                            *reference["impact_velocity_m_s"])
                for i in range(4):
                    coarse_error = abs(coarse[i] - expected[i])
                    fine_error = abs(fine[i] - expected[i])
                    self.assertLess(fine_error, 2e-5)
                    self.assertLessEqual(fine_error, coarse_error + 2e-10)
                self.assertGreaterEqual(
                    reference["specific_mechanical_energy_loss_m2_s2"],
                    -1e-7)

    def test_invalid_physics_inputs_rejected(self):
        valid = dict(launch_speed_m_s=20.0, angle_deg=30.0,
                     initial_height_m=2.0, gravity_m_s2=9.81,
                     linear_drag_s_inv=0.02)
        for key, bad in (("gravity_m_s2", 0.0),
                         ("linear_drag_s_inv", -0.1),
                         ("launch_speed_m_s", float("nan")),
                         ("angle_deg", 91.0)):
            with self.subTest(key=key):
                self.assertRaises(ValueError, solve_earth_projectile,
                                  **{**valid, key: bad})


if __name__ == "__main__":
    unittest.main()

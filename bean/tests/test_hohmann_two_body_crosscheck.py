"""Independent transfer endpoint check across existing analytical and numerical solvers.

Synthetic, pre-registered Earth-mu cases. Tests deterministic reference-tool
agreement, not autonomous BEAN learning or mission-grade propagation.
"""
import math
import unittest

from bean.engineering.spaceflight import BODIES, hohmann_reference
from bean.engineering.two_body import propagate_two_body


class HohmannNumericalCrosscheck(unittest.TestCase):
    def test_two_direction_transfer_endpoint_and_conservation(self):
        mu = BODIES["earth"]["mu_km3_s2"]
        # Fixed before execution; no fitting to results. Both directions matter.
        for start, end in ((7000.0, 12000.0), (12000.0, 7000.0)):
            with self.subTest(start=start, end=end):
                a = (start + end) / 2.0
                transfer_speed = math.sqrt(mu * (2.0 / start - 1.0 / a))
                target_speed = math.sqrt(mu * (2.0 / end - 1.0 / a))
                reference = hohmann_reference(
                    mu_km3_s2=mu, start_radius_km=start, end_radius_km=end)
                half_period = math.pi * math.sqrt(a**3 / mu)
                self.assertAlmostEqual(
                    reference["transfer_time_days"] * 86400, half_period,
                    delta=1e-7)
                # A numerical propagation uses velocity-Verlet, not the
                # Hohmann reference's analytic endpoint formula.
                def propagate(n):
                    return propagate_two_body(
                        mu_km3_s2=mu, minimum_radius_km=6371.0,
                        position_km=[start, 0.0, 0.0],
                        velocity_km_s=[0.0, transfer_speed, 0.0],
                        step_seconds=half_period / n, steps=n)
                coarse = propagate(2000)
                fine = propagate(4000)
                def errors(out):
                    x, y, z = out["final_position_km"]
                    vx, vy, vz = out["final_velocity_km_s"]
                    return (abs(math.hypot(x, y, z) - end),
                            abs(math.hypot(vx, vy, vz) - target_speed))
                coarse_r, coarse_v = errors(coarse)
                fine_r, fine_v = errors(fine)
                # Second-order global convergence for fixed-step Verlet.
                self.assertLess(fine_r, max(1e-6, coarse_r * 0.4))
                self.assertLess(fine_v, max(1e-8, coarse_v * 0.4))
                self.assertLess(fine_r, 0.02)  # km
                self.assertLess(fine_v, 0.00002)  # km/s
                self.assertLess(fine["max_scaled_specific_energy_drift"], 1e-5)
                self.assertLess(
                    fine["max_scaled_angular_momentum_vector_drift"], 1e-9)
                # Arrival is on the opposite side, not merely at same radius.
                self.assertLess(fine["final_position_km"][0], 0)
                self.assertLess(abs(fine["final_position_km"][1]), 0.05)

    def test_invalid_transfer_below_body_is_rejected(self):
        mu = BODIES["earth"]["mu_km3_s2"]
        with self.assertRaises(ValueError):
            propagate_two_body(
                mu_km3_s2=mu, minimum_radius_km=6371,
                position_km=[6300, 0, 0], velocity_km_s=[0, 8, 0],
                step_seconds=1, steps=1)


if __name__ == "__main__":
    unittest.main()

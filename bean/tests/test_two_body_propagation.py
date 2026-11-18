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

    def test_gravity_vector_is_inward_and_inverse_square(self):
        # Independent Newtonian GM/r^2 check, including the propagated state.
        near = reference(radius=7000., dt=1., steps=1)
        far = reference(radius=14000., dt=1., steps=1)
        g_near = near["initial_gravitational_acceleration_km_s2"]
        g_far = far["initial_gravitational_acceleration_km_s2"]
        self.assertEqual(near["units"]["gravitational_acceleration"], "km/s^2")
        self.assertAlmostEqual(g_near[0], -MU / 7000.**2, places=12)
        self.assertEqual(g_near[1:], [0., 0.])
        self.assertAlmostEqual(g_near[0] / g_far[0], 4., places=12)
        final_pos = near["final_position_km"]
        final_g = near["final_gravitational_acceleration_km_s2"]
        self.assertLess(sum(p * a for p, a in zip(final_pos, final_g)), 0.)
        self.assertAlmostEqual(math.hypot(*final_g),
                               MU / math.hypot(*final_pos)**2, places=12)

    def test_initial_conic_circular_and_elliptical(self):
        circular = reference(radius=7000, dt=1, steps=1)["initial_conic_reference"]
        self.assertEqual(circular["classification"], "bound")
        self.assertAlmostEqual(circular["eccentricity"], 0, delta=1e-12)
        self.assertAlmostEqual(circular["periapsis_radius_km"], 7000, delta=1e-6)
        self.assertAlmostEqual(circular["apoapsis_radius_km"], 7000, delta=1e-6)
        self.assertFalse(circular["periapsis_intersects_body"])
        self.assertFalse(circular["degenerate_radial_path"])

        rp, ra = 7000., 14000.
        a = (rp + ra) / 2
        vp = math.sqrt(MU * (2 / rp - 1 / a))
        ellipse = reference(radius=rp, velocity=vp, dt=1, steps=1)["initial_conic_reference"]
        self.assertEqual(ellipse["classification"], "bound")
        self.assertAlmostEqual(ellipse["eccentricity"], 1/3, delta=1e-12)
        self.assertAlmostEqual(ellipse["semimajor_axis_km"], a, delta=1e-6)
        self.assertAlmostEqual(ellipse["periapsis_radius_km"], rp, delta=1e-6)
        self.assertAlmostEqual(ellipse["apoapsis_radius_km"], ra, delta=1e-6)

    def test_initial_conic_escape_and_hyperbolic(self):
        escape = math.sqrt(2 * MU / 7000)
        parabola = reference(radius=7000, velocity=escape, dt=1, steps=1)[
            "initial_conic_reference"]
        self.assertEqual(parabola["classification"], "near_parabolic")
        self.assertAlmostEqual(parabola["eccentricity"], 1, delta=1e-12)
        self.assertAlmostEqual(parabola["periapsis_radius_km"], 7000, delta=1e-6)
        self.assertIsNone(parabola["apoapsis_radius_km"])
        self.assertIsNone(parabola["semimajor_axis_km"])

        hyperbola = reference(radius=7000, velocity=1.1 * escape, dt=1, steps=1)[
            "initial_conic_reference"]
        self.assertEqual(hyperbola["classification"], "unbound")
        self.assertGreater(hyperbola["eccentricity"], 1)
        self.assertLess(hyperbola["semimajor_axis_km"], 0)
        self.assertIsNone(hyperbola["apoapsis_radius_km"])

    def test_initial_conic_radial_impact_warning(self):
        radial = propagate_two_body(
            mu_km3_s2=MU, minimum_radius_km=EARTH_RADIUS,
            position_km=[7000, 0, 0], velocity_km_s=[0, 0, 0],
            step_seconds=1, steps=1)["initial_conic_reference"]
        self.assertEqual(radial["classification"], "bound")
        self.assertTrue(radial["degenerate_radial_path"])
        self.assertTrue(radial["periapsis_intersects_body"])
        self.assertAlmostEqual(radial["periapsis_radius_km"], 0, delta=1e-12)
        self.assertAlmostEqual(radial["apoapsis_radius_km"], 7000, delta=1e-6)

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



    def test_seeded_three_dimensional_rotation_covariance(self):
        """Independent SO(3) symmetry check on held-out inertial states.

        Seed 20261118; eight synthetic tilted circular states, 120 fixed
        steps per state. Rotate both initial vectors using Rodrigues'
        formula and compare with rotated original output. This verifies
        vector direction handling, not adaptive learning or ephemerides.
        A deliberately wrong velocity rotation is the negative control.
        """
        import random
        rng = random.Random(20261118)

        def rotate(vector, axis, angle):
            c, s = math.cos(angle), math.sin(angle)
            dot = sum(a * b for a, b in zip(axis, vector))
            cross = (axis[1]*vector[2] - axis[2]*vector[1],
                     axis[2]*vector[0] - axis[0]*vector[2],
                     axis[0]*vector[1] - axis[1]*vector[0])
            return [c*v + s*w + (1-c)*dot*a
                    for v, w, a in zip(vector, cross, axis)]

        for case in range(8):
            radius = rng.uniform(EARTH_RADIUS + 300, EARTH_RADIUS + 5000)
            speed = math.sqrt(MU / radius)
            pos, vel = [radius, 0., 0.], [0., speed, 0.]
            axis_raw = [rng.uniform(-1, 1) for _ in range(3)]
            length = math.sqrt(sum(v*v for v in axis_raw))
            axis = [v / length for v in axis_raw]
            angle = rng.uniform(0.35, 2.8)
            rotated_pos = rotate(pos, axis, angle)
            rotated_vel = rotate(vel, axis, angle)

            def propagate(position, velocity):
                return propagate_two_body(
                    mu_km3_s2=MU, minimum_radius_km=EARTH_RADIUS,
                    position_km=position, velocity_km_s=velocity,
                    step_seconds=4., steps=120)

            baseline = propagate(pos, vel)
            candidate = propagate(rotated_pos, rotated_vel)
            expected_pos = rotate(baseline["final_position_km"], axis, angle)
            expected_vel = rotate(baseline["final_velocity_km_s"], axis, angle)
            position_residual = math.dist(candidate["final_position_km"], expected_pos)
            velocity_residual = math.dist(candidate["final_velocity_km_s"], expected_vel)
            wrong_control = propagate(rotated_pos, vel)
            wrong_residual = math.dist(wrong_control["final_position_km"], expected_pos)
            with self.subTest(case=case):
                self.assertLess(position_residual, 1e-7)
                self.assertLess(velocity_residual, 1e-10)
                self.assertGreater(wrong_residual, 1.0)
                self.assertAlmostEqual(
                    baseline["initial_specific_energy_km2_s2"],
                    candidate["initial_specific_energy_km2_s2"], delta=1e-11)
                self.assertAlmostEqual(
                    baseline["max_scaled_specific_energy_drift"],
                    candidate["max_scaled_specific_energy_drift"], delta=1e-11)

if __name__ == "__main__":
    unittest.main()

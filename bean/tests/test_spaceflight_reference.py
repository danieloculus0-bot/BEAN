"""Deterministic independent reference and negative-case tests for BEAN spaceflight."""
import math
import unittest

from bean.engineering.spaceflight import (
    AU_KM, BODIES, REQUEST_SCHEMA, G0_M_S2, acceleration_reference,
    departure_burn_reference, hohmann_reference, mars_transfer_reference,
    orbital_reference, rocket_reference, solve_spaceflight_reference,
    vis_viva_speed,
)


class TestSpaceflightReference(unittest.TestCase):
    def test_earth_leo(self):
        out = orbital_reference(body="earth", altitude_km=400)
        self.assertAlmostEqual(out["circular_speed_km_s"], 7.67, delta=0.03)
        self.assertAlmostEqual(out["circular_period_s"] / 60, 92.4, delta=1.0)
        self.assertAlmostEqual(out["escape_speed_km_s"] / out["circular_speed_km_s"], math.sqrt(2))

    def test_surface_gravity_earth_mars(self):
        earth = orbital_reference(body="earth", altitude_km=0)
        mars = orbital_reference(body="mars", altitude_km=0)
        self.assertAlmostEqual(earth["local_gravity_m_s2"], 9.82, delta=0.05)
        self.assertAlmostEqual(mars["local_gravity_m_s2"], 3.73, delta=0.1)

    def test_vis_viva_circular_and_elliptic(self):
        mu = BODIES["earth"]["mu_km3_s2"]
        v = vis_viva_speed(mu_km3_s2=mu, radius_km=7000, semimajor_axis_km=7000)
        self.assertAlmostEqual(v, math.sqrt(mu / 7000), places=10)
        self.assertGreater(vis_viva_speed(mu_km3_s2=mu, radius_km=7000, semimajor_axis_km=10000), v)

    def test_hohmann_equal_radius_zero_delta_v(self):
        out = hohmann_reference(mu_km3_s2=BODIES["earth"]["mu_km3_s2"],
                                start_radius_km=7000, end_radius_km=7000)
        self.assertAlmostEqual(out["total_impulsive_delta_v_km_s"], 0, places=12)

    def test_hohmann_reverse_symmetry(self):
        mu = BODIES["earth"]["mu_km3_s2"]
        a = hohmann_reference(mu_km3_s2=mu, start_radius_km=7000, end_radius_km=15000)
        b = hohmann_reference(mu_km3_s2=mu, start_radius_km=15000, end_radius_km=7000)
        self.assertAlmostEqual(a["total_impulsive_delta_v_km_s"], b["total_impulsive_delta_v_km_s"])
        self.assertAlmostEqual(a["transfer_time_days"], b["transfer_time_days"])

    def test_mars_transfer_reference_order_of_magnitude(self):
        out = mars_transfer_reference()
        self.assertAlmostEqual(out["transfer_time_days"], 259, delta=3)
        self.assertAlmostEqual(out["departure_delta_v_km_s"], 2.94, delta=0.1)
        self.assertAlmostEqual(out["arrival_delta_v_km_s"], 2.65, delta=0.1)
        self.assertAlmostEqual(out["start_radius_km"], AU_KM)
        self.assertIn("NOT launch-to-LEO", out["interpretation"])

    def test_rocket_mass_conservation_and_inversion(self):
        out = rocket_reference(delta_v_km_s=3.0, isp_s=300, dry_mass_kg=1000)
        self.assertGreater(out["propellant_mass_kg"], 0)
        self.assertAlmostEqual(out["initial_mass_kg"] - out["propellant_mass_kg"], 1000)
        self.assertAlmostEqual(out["specific_impulse_s"] * G0_M_S2 *
                               math.log(out["mass_ratio"]) / 1000, 3.0)
        self.assertEqual(rocket_reference(delta_v_km_s=0, isp_s=300,
                                          dry_mass_kg=100)["propellant_mass_kg"], 0)

    def test_earth_escape_and_hyperbolic_excess(self):
        a = departure_burn_reference(body="earth", parking_altitude_km=400,
                                     v_infinity_km_s=0)
        b = departure_burn_reference(body="earth", parking_altitude_km=400,
                                     v_infinity_km_s=3)
        self.assertAlmostEqual(a["required_impulsive_delta_v_km_s"],
                               (math.sqrt(2) - 1) * a["circular_parking_speed_km_s"])
        self.assertGreater(b["required_impulsive_delta_v_km_s"],
                           a["required_impulsive_delta_v_km_s"])

    def test_ideal_acceleration(self):
        d = acceleration_reference(delta_v_km_s=1, acceleration_m_s2=10)
        self.assertAlmostEqual(d["ideal_acceleration_time_s"], 100)
        self.assertAlmostEqual(d["ideal_distance_during_acceleration_km"], 50)

    def test_schema_and_provenance(self):
        r = solve_spaceflight_reference({"schema": REQUEST_SCHEMA,
                "calculation": "mars_transfer", "parameters": {}, "source_ref": "test-case"})
        self.assertFalse(r["flight_qualified"])
        self.assertFalse(r["independently_validated"])
        self.assertEqual(r["source_ref"], "test-case")
        self.assertEqual(r["data_provenance"]["date_specific_ephemeris"], "not_fetched")

    def test_bad_inputs_refused(self):
        valid = {"schema": REQUEST_SCHEMA, "calculation": "orbit",
                 "parameters": {"body": "earth", "altitude_km": 400}}
        bad = [
            {"schema": "unknown", "calculation": "orbit", "parameters": {}},
            {**valid, "parameters": {"body": "earth", "altitude_km": -5}},
            {**valid, "parameters": {"body": "jupiter", "altitude_km": 500}},
            {**valid, "parameters": {"body": "earth", "altitude_km": True}},
            {**valid, "parameters": {"body": "earth", "altitude_km": float("nan")}},
            {**valid, "parameters": {"body": "earth", "altitude_km": "400"}},
            {**valid, "parameters": {"body": "earth", "altitude_km": 400, "secret": 1}},
            {**valid, "calculation": "unknown"},
            {**valid, "source_ref": ""},
            {**valid, "extra": 7},
        ]
        for case in bad:
            with self.subTest(case=case), self.assertRaises(ValueError):
                solve_spaceflight_reference(case)
        for kwargs in (
            dict(delta_v_km_s=1, isp_s=0, dry_mass_kg=1),
            dict(delta_v_km_s=-1, isp_s=300, dry_mass_kg=1),
            dict(delta_v_km_s=100000, isp_s=1, dry_mass_kg=10),
        ):
            with self.assertRaises(ValueError):
                rocket_reference(**kwargs)
        with self.assertRaises(ValueError):
            vis_viva_speed(mu_km3_s2=398600, radius_km=30000, semimajor_axis_km=7000)
        with self.assertRaises(ValueError):
            acceleration_reference(delta_v_km_s=1, acceleration_m_s2=0)


if __name__ == "__main__":
    unittest.main()

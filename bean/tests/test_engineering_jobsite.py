"""BEAN Jobsite: numerical invariants, fail-closed construction screening."""
import json
import math
import unittest
from unittest.mock import patch

from bean.engineering.jobsite import (
    count_studs, analyze_beams, evaluate_request, rules_catalog,
)


def member(name="A", **changed):
    data = {
        "id": name, "width_in": 1.5, "depth_in": 3.5,
        "span_ft": 10., "load_plf": 40.,
        "modulus_psi": 1200000., "allowable_bending_psi": 900.,
        "allowable_shear_psi": 135., "deflection_limit_ratio": 360.,
    }
    data.update(changed)
    return data


class BeanJobsiteTests(unittest.TestCase):
    def test_twenty_foot_wall_with_16_inch_centers(self):
        x = count_studs(20, 16)
        self.assertEqual(x["base_full_height_studs"], 16)
        self.assertFalse(x["building_code_compliant"])
        self.assertIn("headers", x["additional_materials_not_included"])

    def test_nonintegral_wall_always_has_end_member(self):
        self.assertEqual(count_studs(10,16)["base_full_height_studs"], 9)
        self.assertEqual(count_studs(10,24)["base_full_height_studs"], 6)

    def test_openings_cannot_be_silently_ignored(self):
        with self.assertRaisesRegex(ValueError,"Openings"):
            count_studs(20,16,openings=1)
        for bad in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                count_studs(bad,16)

    def test_baseline_beam_equations_independent_of_input_codes(self):
        x = analyze_beams([member()])["members"][0]
        # w = 40/12 lb/in, span = 120 in, M = w*L^2/8 = 6000 lb-in
        self.assertAlmostEqual(x["calculated"]["peak_moment_lb_in"],6000.)
        self.assertAlmostEqual(x["calculated"]["peak_shear_lb"],200.)
        self.assertAlmostEqual(x["calculated"]["bending_stress_psi"],6000/(1.5*3.5**2/6))
        self.assertAlmostEqual(x["calculated"]["shear_stress_psi"],1.5*200/(1.5*3.5))
        i=1.5*3.5**3/12
        expected=5*(40/12)*120**4/(384*1200000*i)
        self.assertAlmostEqual(x["calculated"]["deflection_in"],expected)
        self.assertEqual(x["screen_status"],"over_supplied_limit")
        self.assertGreater(x["minimum_idealized_depth_in"],3.5)

    def test_weakest_is_most_utilized_not_smallest_member(self):
        x=analyze_beams([
            member("small",load_plf=1,span_ft=4),
            member("loaded",depth_in=7.25,load_plf=100,span_ft=16),
        ])
        self.assertEqual(x["weakest_member_by_utilization"],"loaded")
        self.assertEqual(x["ranking"][0],"loaded")
        self.assertTrue(x["requires_qualified_review"])
        self.assertFalse(x["real_fea_solve_performed"])
        self.assertFalse(x["building_code_compliant"])

    def test_approved_limits_not_guessed(self):
        missing=member()
        del missing["allowable_bending_psi"]
        with self.assertRaisesRegex(ValueError,"allowable_bending_psi"):
            analyze_beams([missing])
        defaults = {
            "allowable_bending_psi":900.,"allowable_shear_psi":135.,
            "modulus_psi":1200000.,"deflection_limit_ratio":360.,
        }
        minimal={"id":"2x4","nominal_size":"2x4","span_ft":8,"load_plf":0}
        result=analyze_beams([minimal],defaults)
        self.assertEqual(result["members"][0]["geometry_in"]["depth"],3.5)
        self.assertEqual(result["members"][0]["worst_utilization"],0.)
        self.assertEqual(result["mitigations"],[])

    def test_zero_warnings_do_not_mean_code_approval(self):
        x = analyze_beams([member(span_ft=2,load_plf=1)])
        self.assertEqual(x["status"],"screen_only_within_supplied_limits")
        self.assertFalse(x["building_code_compliant"])

    def test_more_load_more_utilization_and_required_depth(self):
        low = analyze_beams([member(load_plf=10)])["members"][0]
        high = analyze_beams([member(load_plf=20)])["members"][0]
        self.assertAlmostEqual(high["calculated"]["bending_stress_psi"],
                               2*low["calculated"]["bending_stress_psi"])
        self.assertAlmostEqual(high["minimum_idealized_depth_in"]/low["minimum_idealized_depth_in"],
                               2**(1/3),delta=0.07)

    def test_invalid_beams_refused_without_results(self):
        wrong=[
            member(span_ft=0),member(depth_in=-1),member(load_plf=-10),
            member(modulus_psi=float("nan")),member(deflection_limit_ratio=1),
            member(allowable_bending_psi=0),member(width_in=True),
        ]
        for row in wrong:
            with self.subTest(row=row),self.assertRaises(ValueError):
                analyze_beams([row])
        with self.assertRaisesRegex(ValueError,"unique"):
            analyze_beams([member("A"),member("A")])

    def test_versioned_json_contract(self):
        x=evaluate_request({"schema":"bean.jobsite_request.v1","operation":"wall_studs",
                            "length_ft":20,"spacing_in":16})
        self.assertEqual(x["base_full_height_studs"],16)
        y=evaluate_request({"schema":"bean.jobsite_request.v1","operation":"beam_check",
                            "members":[member()]})
        self.assertEqual(y["weakest_member_by_utilization"],"A")
        self.assertFalse(y["training_weights_updated"])
        with self.assertRaisesRegex(ValueError,"Unknown"):
            evaluate_request({"schema":"bean.jobsite_request.v1","operation":"wall_studs",
                              "length_ft":20,"spacing_in":16,"secret":1})

    def test_rule_bundle_explicitly_denies_code_approval(self):
        r=rules_catalog()
        self.assertFalse(r["rules"]["straight_wall_takeoff"]["code_approval"])
        self.assertFalse(r["rules"]["simply_supported_uniform_beam"]["code_approval"])
        self.assertFalse(r["output_policy"]["autonomous_design_approval"])


if __name__=="__main__":
    unittest.main()

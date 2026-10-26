"""Exact stud-grid takeoffs with explicit rough openings and no invented codes."""
import unittest

from bean.engineering.framing import takeoff_wall
from bean.engineering.jobsite import evaluate_request


def opening(start, width, kings=1, jacks=1):
    return {"start_in":start, "width_in":width,
            "extra_king_studs_per_side":kings,"jack_studs_per_side":jacks}


class WallFramingTakeoffTests(unittest.TestCase):
    def test_twenty_foot_straight_wall_no_openings(self):
        r=takeoff_wall(20,16,[])
        self.assertEqual(r["baseline_grid_studs"],16)
        self.assertEqual(r["minimum_specified_2x4_pieces_before_other_framing"],16)
        self.assertFalse(r["building_code_compliant"])
        self.assertTrue(r["requires_verified_framing_plan"])

    def test_ten_foot_wall_keeps_a_stud_at_short_end_bay(self):
        r=takeoff_wall(10,16,[])
        self.assertEqual(r["baseline_grid_studs"],9)
        self.assertEqual(r["minimum_specified_2x4_pieces_before_other_framing"],9)

    def test_explicit_opening_removes_grid_positions_and_adds_specified_framing(self):
        # 20 ft @ 16-inch centers => 16 baseline; rough span (64,104)
        # removes centers 80 and 96 only. Add 2 extra kings and 2 jacks.
        r=takeoff_wall(20,16,[opening(64,40)])
        self.assertEqual(r["studs_removed_inside_rough_openings"],2)
        self.assertEqual(r["removed_center_positions_in"],[80,96])
        self.assertEqual(r["baseline_full_height_studs_remaining"],14)
        self.assertEqual(r["extra_full_height_king_studs_specified"],2)
        self.assertEqual(r["short_jack_studs_specified"],2)
        self.assertEqual(r["minimum_specified_2x4_pieces_before_other_framing"],18)
        self.assertIn("headers",r["not_included"])

    def test_no_guessed_extra_kings_or_jacks(self):
        r=takeoff_wall(20,16,[opening(64,40,0,0)])
        self.assertEqual(r["extra_full_height_king_studs_specified"],0)
        self.assertEqual(r["short_jack_studs_specified"],0)
        self.assertEqual(r["minimum_specified_2x4_pieces_before_other_framing"],14)

    def test_multiple_openings_validated_independently(self):
        r=takeoff_wall(20,16,[opening(64,40),opening(140,32,1,2)])
        self.assertEqual(r["opening_count"],2)
        self.assertEqual(r["extra_full_height_king_studs_specified"],4)
        self.assertEqual(r["short_jack_studs_specified"],6)
        self.assertEqual(len(r["removed_center_positions_in"]),4)

    def test_too_close_touching_and_overlapping_openings_rejected(self):
        for entries in (
            [opening(64,40),opening(90,30)],
            [opening(64,40),opening(104,20)],
            [opening(0,24)], [opening(220,20)],
            [opening(-1,24)], [opening(50,0)],
        ):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                takeoff_wall(20,16,entries)

    def test_missing_framing_details_rejected(self):
        request=opening(64,40)
        request.pop("jack_studs_per_side")
        with self.assertRaisesRegex(ValueError,"explicit king/jack"):
            takeoff_wall(20,16,[request])

    def test_invalid_counts_and_opening_positions_rejected(self):
        for bad in (1.5, True, -1, 21):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                takeoff_wall(20,16,[opening(64,40,1,bad)])
        with self.assertRaisesRegex(ValueError,"too many"):
            takeoff_wall(20,.000001,[])

    def test_external_versioned_jobsite_api_executes_same_framing_module(self):
        result=evaluate_request({
            "schema":"bean.jobsite_request.v1","operation":"wall_layout",
            "length_ft":20,"spacing_in":16,
            "openings":[opening(64,40)]})
        self.assertEqual(result["minimum_specified_2x4_pieces_before_other_framing"],18)
        with self.assertRaisesRegex(ValueError,"Unknown wall-layout"):
            evaluate_request({
                "schema":"bean.jobsite_request.v1","operation":"wall_layout",
                "length_ft":20,"spacing_in":16,"openings":[],
                "made_up_code_strength":1500})

if __name__=="__main__":
    unittest.main()

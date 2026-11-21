"""Generic deterministic and adversarial acceptance cases for BEAN rigid-body solver."""
import math
import unittest
from bean.engineering.rigid_body import solve_rigid_body_balance as solve


def base(**overrides):
    b = {"parts":[{"mass_kg":2,"center_m":[0,0],"intrinsic_inertia_kg_m2":.01}],
         "pivot_m":[0,-.1],"spin_rps":1,"fill_fractions":[0,.5,1]}
    b.update(overrides)
    return b


TANK = {"capacity_l":.2,"inner_radius_m":.04,"base_center_m":[0,.05],
        "fluid_density_kg_per_l":1.0}


class TestRigidBody(unittest.TestCase):
    def test_zero_offset_no_torque(self):
        r=solve(base(pivot_m=[0,0]))["states"][0]
        self.assertEqual(r["peak_gravity_torque_nm"],0)
        self.assertEqual(r["radial_reaction_n"],0)

    def test_reference_torque(self):
        r=solve(base())["states"][0]
        self.assertAlmostEqual(r["peak_gravity_torque_nm"],2*9.80665*.1)
        self.assertAlmostEqual(r["inertia_kg_m2"],.01+2*.1**2)

    def test_spin_speed_force_quadratic(self):
        a=solve(base(spin_rps=1))["states"][0]
        b=solve(base(spin_rps=2))["states"][0]
        self.assertAlmostEqual(b["radial_reaction_n"],a["radial_reaction_n"]*4)
        self.assertAlmostEqual(b["rotational_energy_j"],a["rotational_energy_j"]*4)
        self.assertEqual(b["peak_gravity_torque_nm"],a["peak_gravity_torque_nm"])

    def test_fill_mass_conservation(self):
        a=solve(base(reservoir=TANK))["states"]
        self.assertAlmostEqual(a[0]["mass_kg"],2)
        self.assertAlmostEqual(a[1]["mass_kg"],2.1)
        self.assertAlmostEqual(a[2]["mass_kg"],2.2)

    def test_uniform_cylinder_centroid(self):
        a=solve(base(parts=[{"mass_kg":0,"center_m":[0,0]}],reservoir=TANK,fill_fractions=[1],pivot_m=[0,0]))["states"][0]
        h=.2/1000/(math.pi*.04**2)
        self.assertAlmostEqual(a["center_of_mass_m"][1],.05+h/2)

    def test_parallel_axis(self):
        a=solve(base())["states"][0]["inertia_kg_m2"]
        b=solve(base(pivot_m=[0,-.2]))["states"][0]["inertia_kg_m2"]
        self.assertAlmostEqual(b-a,2*(.2**2-.1**2))

    def test_minimax_pivot_candidates(self):
        r=solve(base(pivot_candidates_m=[[0,-.1],[0,0],[0,-.05]]))
        self.assertEqual(r["recommended_candidate"]["pivot_m"],[0,0])

    def test_candidate_clearance(self):
        r=solve(base(pivot_candidates_m=[[0,0],[0,-.04],[0,-.09]],maximum_pivot_y_m=-.05,pivot_m=[0,-.1]))
        self.assertEqual(len(r["ranked_pivot_candidates"]),1)
        self.assertEqual(r["recommended_candidate"]["pivot_m"],[0,-.09])

    def test_baseline_clearance_rejection(self):
        with self.assertRaises(ValueError):solve(base(maximum_pivot_y_m=-.12))

    def test_bad_fills_rejected(self):
        for vals in ([],[-.1],[1.01],[float('nan')],[True],list(range(102))):
            with self.subTest(vals=str(vals)[:20]),self.assertRaises(ValueError):solve(base(fill_fractions=vals))

    def test_bad_part_mass_rejected(self):
        for v in (-.1,float('inf'),'0.5',True):
            with self.subTest(v=v),self.assertRaises(ValueError):solve(base(parts=[{"mass_kg":v,"center_m":[0,0]}]))

    def test_bad_reservoir_rejected(self):
        for key,bad in (("capacity_l",0),("inner_radius_m",0),("fluid_density_kg_per_l",-1),("inner_radius_m",float('nan'))):
            tank=dict(TANK);tank[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):solve(base(reservoir=tank))

    def test_zero_total_mass_rejected(self):
        with self.assertRaises(ValueError):solve(base(parts=[{"mass_kg":0,"center_m":[0,0]}]))

    def test_no_candidate_is_not_approved(self):
        r=solve(base(maximum_pivot_y_m=-.2,pivot_m=[0,-.25],pivot_candidates_m=[[0,0]]))
        self.assertIsNone(r["recommended_candidate"])
        self.assertEqual(r["ranked_pivot_candidates"],[])

    def test_repeated_deterministic(self):
        r=base(reservoir=TANK,pivot_candidates_m=[[0,-.1],[0,-.05]])
        self.assertEqual(solve(r),solve(r))

    def test_no_physical_certification(self):
        r=solve(base())
        self.assertEqual(r["status"],"simplified_synthetic_reference")
        self.assertIn("no slosh, splashing, grip biomechanics, friction or structural flexibility",r["assumptions"])


if __name__=='__main__':unittest.main()

"""BEAN independently calculates mechanical stress, not invented CAD FEA."""
import math
import unittest

from bean.engineering.stress_solver import solve_stress_reference

def specimen(**loads):
    state = dict(axial_force_n=0., bending_moment_y_nmm=0.,
                 bending_moment_z_nmm=0., torque_x_nmm=0.)
    state.update(loads)
    return {"schema":"bean.stress_request.v1",
            "geometry":{"shape":"solid_circular_shaft","radius_mm":10.},
            "loads":state,"point_mm":[0.,10.],"source_ref":"unit-test"}

class BeanStressSolverTests(unittest.TestCase):
    def test_torsion_matches_saint_venant(self):
        v=solve_stress_reference(specimen(torque_x_nmm=10000.))
        self.assertAlmostEqual(v["tensor_mpa"]["sxy"],-20/math.pi)
        self.assertAlmostEqual(v["tensor_mpa"]["sxz"],0.)
        self.assertAlmostEqual(v["von_mises_mpa"],20*math.sqrt(3)/math.pi)
        self.assertFalse(v["trained_surrogate"])
        self.assertTrue(v["review_required"])

    def test_axial_stress(self):
        v=solve_stress_reference(specimen(axial_force_n=1000.))
        self.assertAlmostEqual(v["tensor_mpa"]["sxx"],10/math.pi)
        self.assertAlmostEqual(v["von_mises_mpa"],10/math.pi)

    def test_bending_tension_and_compression(self):
        a=specimen(bending_moment_y_nmm=5000.)
        first=solve_stress_reference(a)["tensor_mpa"]["sxx"]
        a["point_mm"]=[0.,-10.]
        self.assertAlmostEqual(solve_stress_reference(a)["tensor_mpa"]["sxx"],-first)
        self.assertAlmostEqual(first,20/math.pi)

    def test_combined_axial_bending_torsion(self):
        v=solve_stress_reference(specimen(
            axial_force_n=1000., bending_moment_y_nmm=5000., torque_x_nmm=10000.))
        sigma=30/math.pi
        tau=20/math.pi
        self.assertAlmostEqual(v["tensor_mpa"]["sxx"],sigma)
        self.assertAlmostEqual(v["von_mises_mpa"],math.sqrt(sigma*sigma+3*tau*tau))

    def test_zero_load_zero_stress(self):
        self.assertEqual(solve_stress_reference(specimen())["von_mises_mpa"],0.)

    def test_unknown_shapes_bad_coordinates_and_nans_refused(self):
        for change in (
            lambda r:r["geometry"].update(shape="assembly"),
            lambda r:r.update(point_mm=[20.,0.]),
            lambda r:r["loads"].update(torque_x_nmm=float("nan")),
            lambda r:r["loads"].update(axial_force_n="100"),
            lambda r:r["geometry"].update(radius_mm=0),
            lambda r:r.update(extra="unsupported"),
        ):
            q=specimen()
            change(q)
            with self.subTest(q=q), self.assertRaises(ValueError):
                solve_stress_reference(q)

if __name__=="__main__":
    unittest.main()

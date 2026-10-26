"""Reject false numerical and provenance claims in imported native FEA reports."""
import math
import unittest
import copy
from types import SimpleNamespace
from unittest.mock import patch

from bean.engineering.fea_evidence import crosscheck_native_torsion


def source_report():
    T=10000.
    r=10.
    L=100.
    E=200000.
    nu=.25
    G=E/(2*(1+nu))
    J=math.pi*r**4/2
    theta=T*L/(G*J)
    tau=T*r/J
    records=[]
    for size,elements,theta_factor,reaction_factor in (
        (6.,832,1.0000652,1.0000000211),
        (4.,2541,1.0000291,1.0000000277),
    ):
        actual=theta*theta_factor
        support=-T*reaction_factor
        records.append({
            "status":"pass","mesh_size_mm":size,
            "elements":elements,
            "measured_tip_twist_rad":actual,
            "twist_relative_error":abs(actual-theta)/abs(theta),
            "native_support_moment_nmm":[support,0.,0.],
            "reaction_torque_relative_error":abs(support+T)/T,
            "applied_audit":{"applied_moment_nmm":[T,0.,0.],
                             "applied_force_n":[0.,0.,0.]},
        })
    return {
        "schema":"ezfea.native_circular_torsion.v1",
        "status":"pass","engineering_validation":"not_established",
        "element_type":"C3D10","source_step_sha256":"a"*64,
        "geometry":{"radius_mm":r,"length_mm":L},
        "material":{"youngs_mpa":E,"poisson":nu},
        "torque_nmm":T,
        "reference_tip_twist_rad":theta,
        "reference_surface_shear_mpa":tau,
        "records":records,
    }


class NativeFEAEvidenceTests(unittest.TestCase):
    def test_recomputes_physics_and_never_claims_approval(self):
        result=crosscheck_native_torsion(source_report(),source_ref="manual-test-run")
        self.assertEqual(result["scope"],"solid_circular_shaft_isotropic_linear_elastic_pure_torsion")
        self.assertTrue(result["independently_recomputed_references"])
        self.assertFalse(result["replayed_native_solver"])
        self.assertFalse(result["learning_weights_updated"])
        self.assertFalse(result["design_approval"])
        self.assertEqual(len(result["grids"]),2)
        self.assertEqual(len(result["source_report_sha256"]),64)
        self.assertEqual(result["provenance_status"],"host_attested_not_independently_authenticated")

    def test_existing_bean_command_inbox_records_the_verified_numerical_observation(self):
        from bean.runtime.inbox_handlers import make_handlers
        cmd=make_handlers()["engineering_fea_evidence_review"]
        message=SimpleNamespace(args={"report":source_report(),"source_ref":"test-run"},
                                sender="ezfea")
        with patch("bean.runtime.inbox_handlers.log_event") as log:
            accepted=cmd(message,"test-session")
        self.assertTrue(accepted["independently_recomputed_references"])
        self.assertFalse(accepted["learning_weights_updated"])
        self.assertEqual(log.call_count,1)
        self.assertEqual(log.call_args.kwargs["subtype"],"engineering_native_fea_reference")
        self.assertFalse(log.call_args.kwargs["data"]["source_authenticated"])

    def test_tampered_reference_disallowed(self):
        data=source_report()
        data["reference_tip_twist_rad"]*=1.10
        with self.assertRaisesRegex(ValueError,"references disagree"):
            crosscheck_native_torsion(data)

    def test_reaction_torque_mismatch_is_detected(self):
        data=source_report()
        data["records"][1]["native_support_moment_nmm"][0]=10000
        with self.assertRaisesRegex(ValueError,"disagrees"):
            crosscheck_native_torsion(data)

    def test_fake_fine_mesh_and_unsorted_grid_rejected(self):
        data=source_report()
        data["records"][1]["elements"]=500
        with self.assertRaisesRegex(ValueError,"element count"):
            crosscheck_native_torsion(data)

    def test_invalid_sha_missing_material_nonfinite_measurements_rejected(self):
        for change in (
            lambda r:r.update(source_step_sha256="not-a-hash"),
            lambda r:r.pop("material"),
            lambda r:r["records"][0].update(measured_tip_twist_rad=float("nan")),
            lambda r:r.update(engineering_validation="approved"),
            lambda r:r.update(status="failed"),
            lambda r:r["material"].update(poisson=.5),
        ):
            d=source_report()
            change(d)
            with self.subTest(change=change),self.assertRaises(ValueError):
                crosscheck_native_torsion(d)

    def test_inaccurate_reported_errors_rejected(self):
        data=source_report()
        data["records"][0]["twist_relative_error"]=0
        with self.assertRaisesRegex(ValueError,"reported error disagree"):
            crosscheck_native_torsion(data)

    def test_applied_force_audit_required(self):
        data=source_report()
        data["records"][0]["applied_audit"]["applied_force_n"]=[1000.,0.,0.]
        with self.assertRaisesRegex(ValueError,"unexpected net force"):
            crosscheck_native_torsion(data)


if __name__=="__main__":
    unittest.main()

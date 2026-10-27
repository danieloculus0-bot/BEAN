"""Test learning safety with synthetic FIXTURES, never label fixtures as real runs.

The separate GitHub integration workflow generates its actual labels by
running Gmsh and CalculiX for every train and holdout specimen.
"""
import json
import tempfile
from pathlib import Path
import unittest

from bean.engineering.native_fea_learning import (
    ACTIONS, _source, _state, learn_from_native_dataset,
)


def fixture():
    rows=[]
    for family,metric in (
        ("axial","midspan_abs_sigma_x_mpa"),
        ("bending","tip_displacement_mm"),
        ("torsion","abs_tip_twist_rad"),
    ):
        for split,count in (("train",4),("holdout",10)):
            for idx in range(count):
                reference=10+idx
                # A known positive correction tests the Q learning code.
                observed=reference*1.02 if family=="axial" else reference
                threshold=12.
                rows.append({
                    "case_id":f"{split}-{family}-{idx:02d}",
                    "split":split,"family":family,"geometry_key":f"{family}:{split}:{idx}",
                    "status":"measured","test_origin":"native_step_gmsh_calculix_c3d10",
                    "source_step_sha256":f"{idx+1:064x}",
                    "native_case_path":"fixture_only",
                    "mesh_elements":111,"target_metric":metric,
                    "analytical_reference":reference,"native_measured":observed,
                    "reference_relative_error":abs(observed-reference)/reference,
                    "example_screen_limit":threshold,
                    "actual_exceeds_example_screen":observed>threshold,
                })
    return {
        "schema":"ezfea.real_structural_curriculum.v1",
        "element_type":"C3D10","origin":"UNIT_TEST_FIXTURE_NOT_ACTUAL_NATIVE_RUNS",
        "no_design_approval":True,"failed_or_needs_review":0,
        "cases_planned":42,"cases_executed":42,
        "cases":rows,
    }


class RealFEALearnerSafetyTests(unittest.TestCase):
    def test_calculates_holdout_scores_and_restores_actual_q_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=learn_from_native_dataset(fixture(),tmp)
            self.assertEqual(report["training_q_updates"],12*len(ACTIONS))
            self.assertEqual(len(report["test_cases"]),30)
            self.assertEqual(report["heldout"]["overall"]["n"],30)
            self.assertEqual(report["checkpoint"]["sample_count"],30)
            self.assertTrue(report["no_heldout_reward_updates"])
            self.assertFalse(report["model_weights_trained"])
            self.assertFalse(report["design_approval"])
            self.assertEqual(len((Path(tmp)/"native_training_ledger.jsonl").read_text().splitlines()),60)
            self.assertEqual(len((Path(tmp)/"unseen_geometry_scores.jsonl").read_text().splitlines()),30)
            self.assertTrue((Path(tmp)/"native_fea_q.sqlite").is_file())
            self.assertEqual(report["source_authentication"],"host_attested_not_independently_authenticated")

    def test_geometry_leak_and_missing_holdout_are_refused(self):
        data=fixture()
        data["cases"][-1]["geometry_key"]=data["cases"][0]["geometry_key"]
        with self.assertRaisesRegex(ValueError,"contamination"):
            _source(data)
        data=fixture()
        data["cases"].pop()
        with self.assertRaisesRegex(ValueError,"12 native training and 30"):
            _source(data)

    def test_native_solver_failures_and_tampered_labels_refused(self):
        data=fixture()
        data["cases"][0]["status"]="needs_review"
        with self.assertRaisesRegex(ValueError,"Non-measured"):
            _source(data)
        data=fixture()
        data["cases"][0]["reference_relative_error"]=.89
        with self.assertRaisesRegex(ValueError,"altered"):
            _source(data)
        data=fixture()
        data["cases"][0]["source_step_sha256"]="unverified"
        with self.assertRaisesRegex(ValueError,"source SHA"):
            _source(data)

    def test_unseen_connection_types_are_not_silently_predicted(self):
        with self.assertRaisesRegex(ValueError,"cannot extrapolate"):
            _state("bolted_assembly")


if __name__=="__main__":
    unittest.main()

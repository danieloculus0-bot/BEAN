"""Train BEAN's existing SpongeTD policy on *measured* native FEA outcomes.

The source must be a complete EZ-FEA real STEP/C3D10/CalculiX curriculum
(12 training geometries and >=30 unseen geometries). This learner does not
solve FEA, certify material failure, approve a structure, or infer weld/contact
behavior. It learns whether a small bounded correction to independently
calculated axial stress, bending tip displacement, or shaft twist is beneficial
when compared with the actual native measurement.

The three test geometries sets are disjoint. The checkpoint quality scorer
may withhold promotion even when performance improves; preserve failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from bean.learning.runtime import LearningRuntime

SCHEMA="bean.native_fea_learning.v1"
DOMAIN="native_fea_reference_calibration.v1"
ACTIONS={
    "reference":1.,
    "higher_2pct":1.02,
    "lower_2pct":.98,
    "higher_6pct":1.06,
    "lower_6pct":.94,
}
FAMILIES={"axial","bending","torsion"}


def _finite_positive(value,name):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
        raise ValueError(f"{name}: required finite positive value")
    return float(value)


def _source(records):
    if not isinstance(records,dict) or records.get("schema")!="ezfea.real_structural_curriculum.v1":
        raise ValueError("Not an EZ-FEA native curriculum report")
    if records.get("element_type")!="C3D10" or not records.get("no_design_approval"):
        raise ValueError("Wrong mesh element type or unsupported approval claim")
    cases=records.get("cases")
    if not isinstance(cases,list) or len(cases)<42:
        raise ValueError("Need 12 native training and 30 independent unseen test cases")
    if records.get("failed_or_needs_review")!=0:
        raise ValueError("Unresolved native solver failures cannot become training labels")
    observed=[]
    geom_groups={"train":set(),"holdout":set()}
    ids=set()
    for row in cases:
        if not isinstance(row,dict) or row.get("status")!="measured":
            raise ValueError("Non-measured native case must not be used")
        if row.get("test_origin")!="native_step_gmsh_calculix_c3d10":
            raise ValueError("Case does not assert actual native solver origin")
        name=row.get("case_id")
        split=row.get("split")
        family=row.get("family")
        geo=row.get("geometry_key")
        digest=row.get("source_step_sha256")
        if (not isinstance(name,str) or name in ids or split not in geom_groups or
            family not in FAMILIES or not isinstance(geo,str) or not geo or
            not isinstance(digest,str) or len(digest)!=64 or
            any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("Case is incomplete, duplicate or lacks source SHA")
        ids.add(name)
        if geo in geom_groups[split]:
            raise ValueError("Duplicate physical geometry in partition")
        geom_groups[split].add(geo)
        reference=_finite_positive(row.get("analytical_reference"),"analytical reference")
        target=_finite_positive(row.get("native_measured"),"actual native measurement")
        threshold=_finite_positive(row.get("example_screen_limit"),"example screen limit")
        expected_metric={
            "axial":"midspan_abs_sigma_x_mpa",
            "bending":"tip_displacement_mm",
            "torsion":"abs_tip_twist_rad",
        }[family]
        if row.get("target_metric")!=expected_metric:
            raise ValueError("Wrong physics measurement for family")
        elem=row.get("mesh_elements")
        if type(elem) is not int or elem<=0:
            raise ValueError("No real native mesh element count")
        _finite_positive(row.get("reference_relative_error") or 1e-100,"reference error")
        if not math.isclose(float(row["reference_relative_error"]),
                            abs(target-reference)/reference,rel_tol=1e-7,abs_tol=1e-8):
            raise ValueError("Native reference discrepancy was altered")
        if row.get("actual_exceeds_example_screen")!=(target>threshold):
            raise ValueError("Native example screening label was altered")
        if not isinstance(row.get("native_case_path"),str):
            raise ValueError("Missing original native solve location")
        observed.append(row)
    if geom_groups["train"] & geom_groups["holdout"]:
        raise ValueError("Heldout geometry contamination")
    train=[r for r in observed if r["split"]=="train"]
    held=[r for r in observed if r["split"]=="holdout"]
    if len(train)!=12 or len(held)<30:
        raise ValueError("Training or unseen sample counts are not the planned split")
    if any(sum(r["family"]==family for r in train)<3 or
           sum(r["family"]==family for r in held)<7 for family in FAMILIES):
        raise ValueError("Every structural family needs sufficient train/holdout examples")
    # Recompute hashes from host-supplied data; cannot authenticate provenance.
    digest=hashlib.sha256(json.dumps(records,sort_keys=True,
        separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return train,held,digest


def _state(family):
    if family not in FAMILIES:
        raise ValueError("BEAN cannot extrapolate into unseen assembly/contact/joint physics")
    return {"family":family,"solver":"C3D10",
            "problem":"linear_elastic_single_member_reference"}


def _selected_action(svc,family):
    key=svc.policy.key(svc.scoped(DOMAIN,_state(family)))
    values=svc.policy.q.get(key)
    if values is None or len(values)!=len(ACTIONS):
        raise ValueError(f"BEAN has no trained policy for {family}")
    # Read-only greedy inference, no test-label updates or exploration.
    return list(ACTIONS)[max(range(len(values)),key=lambda i:values[i])]


def _relative_error(truth,pred):
    return abs(pred-truth)/max(abs(truth),1e-15)


def _eval(svc,held):
    results=[]
    for row in held:
        action=_selected_action(svc,row["family"])
        target=row["native_measured"]
        baseline=row["analytical_reference"]
        learned=baseline*ACTIONS[action]
        threshold=row["example_screen_limit"]
        results.append({
            "case_id":row["case_id"],"family":row["family"],
            "geometry_key":row["geometry_key"],
            "native_source_sha256":row["source_step_sha256"],
            "native_measured":target,
            "analytical_prediction":baseline,
            "bean_prediction":learned,
            "bean_choice":action,
            "baseline_relative_error":_relative_error(target,baseline),
            "bean_relative_error":_relative_error(target,learned),
            "example_threshold":threshold,
            "native_example_exceeds_threshold":target>threshold,
            "analytical_example_exceeds_threshold":baseline>threshold,
            "bean_example_exceeds_threshold":learned>threshold,
            "root_cause_code":(
                "BEAN_UNDERPREDICTED" if learned<target*.98 else
                "BEAN_OVERPREDICTED" if learned>target*1.02 else
                "BEAN_NEAR_NATIVE"),
        })
    def summarize(rows):
        base=sum(x["baseline_relative_error"] for x in rows)/len(rows)
        bean=sum(x["bean_relative_error"] for x in rows)/len(rows)
        return {
            "n":len(rows),
            "analytical_mean_relative_error":base,
            "bean_mean_relative_error":bean,
            "relative_error_improvement_percentage_points":100*(base-bean),
            "analytical_screen_accuracy":sum(
                x["analytical_example_exceeds_threshold"]==
                x["native_example_exceeds_threshold"] for x in rows)/len(rows),
            "bean_screen_accuracy":sum(
                x["bean_example_exceeds_threshold"]==
                x["native_example_exceeds_threshold"] for x in rows)/len(rows),
        }
    by_family={family:summarize([x for x in results if x["family"]==family])
               for family in sorted(FAMILIES)}
    return results,{"overall":summarize(results),"families":by_family}


def learn_from_native_dataset(data,output="runs/bean_real_fea_learning"):
    train,held,digest=_source(data)
    root=Path(output)
    root.mkdir(parents=True,exist_ok=True)
    svc=LearningRuntime(root/"native_fea_q.sqlite",actions=tuple(ACTIONS),seed=17)
    observations=[]
    checkpoint=None
    try:
        # TRAIN: every candidate is evaluated against the *same actual
        # CalculiX measurement* (matched counterfactual correction).
        for row in train:
            true=row["native_measured"]
            for action,factor in ACTIONS.items():
                episode=f"{row['case_id']}::{action}"
                selected=svc.choose(
                    episode_id=episode,domain=DOMAIN,
                    state=_state(row["family"]),
                    location_ref=["native_C3D10",row["case_id"]],
                    legal_actions=[action])
                if selected["action"]!=action:
                    raise ValueError("BEAN training action differed from scored action")
                guess=row["analytical_reference"]*factor
                err=_relative_error(true,guess)
                # Rewards derive from real FEA measurements, not independent
                # analytical equations or synthetic idealized repairs.
                reward=1.-min(err,1.)
                feedback=svc.feedback(episode_id=episode,reward=reward,done=True)
                if not feedback["learned"]:
                    raise RuntimeError("BEAN did not update its actual Q policy")
                observations.append({
                    "case_id":row["case_id"],"family":row["family"],
                    "source_step_sha256":row["source_step_sha256"],
                    "action":action,"analytical_reference":row["analytical_reference"],
                    "real_fea_measured":true,"candidate_prediction":guess,
                    "candidate_relative_error":err,"reward":reward,
                    "why":("analytical_baseline" if action=="reference" else
                           "empirical_directional_correction"),
                    "reward_provenance":"host_supplied_native_solver_measurement",
                    "validation":"not_established",
                })
        # TEST: labels never feed training; inference acts on family and
        # independent mechanics, not on a held-out target value.
        results,metrics=_eval(svc,held)
        source_score=-metrics["overall"]["analytical_mean_relative_error"]
        candidate_score=-metrics["overall"]["bean_mean_relative_error"]
        checkpoint_payload={
            "schema":SCHEMA,"input_dataset_sha256":digest,
            "training_real_native_cases":len(train),
            "heldout_geometry_distinct_cases":len(held),
            "training_q_updates":len(observations),
            "native_test_origin":"real_Gmsh_C3D10_CalculiX",
            "actions":ACTIONS,
            "heldout":metrics,"test_cases":results,
            "training_observations":observations,
            "all_training_residuals_kept":True,
            "no_heldout_reward_updates":True,
            "source_authentication":"host_attested_not_independently_authenticated",
            "safety_thresholds":"hypothetical exercise values, not real allowable stresses or design codes",
            "model_weights_trained":False,
            "existing_sponge_td_q_updated":True,
            "design_approval":False,
            "engineering_validation":"not_established",
        }
        receipt=hashlib.sha256(json.dumps(checkpoint_payload,sort_keys=True,
            separators=(",",":"),allow_nan=False).encode()).hexdigest()
        checkpoint=svc.checkpoint(
            baseline=source_score,candidate=candidate_score,
            samples=len(held),evaluation_sha256=receipt)
        checkpoint_payload["checkpoint"]=checkpoint
        checkpoint_payload["receipt_sha256"]=receipt
        (root/"native_fea_learning.json").write_text(
            json.dumps(checkpoint_payload,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        (root/"native_training_ledger.jsonl").write_text(
            "".join(json.dumps(x,sort_keys=True,allow_nan=False)+"\n"
                    for x in observations),encoding="utf-8")
        (root/"unseen_geometry_scores.jsonl").write_text(
            "".join(json.dumps(x,sort_keys=True,allow_nan=False)+"\n"
                    for x in results),encoding="utf-8")
    finally:
        svc.close()
    # Prove actual *BEAN* checkpoint recovery, not just an exported table.
    restored=LearningRuntime(root/"native_fea_q.sqlite",actions=tuple(ACTIONS),seed=17)
    try:
        status=restored.status()
        if (status["q_updates"]!=len(observations) or
            status["checkpoints"]!=1 or status["q_states"]<len(FAMILIES)):
            raise RuntimeError("BEAN real-FEA Q state did not survive restart")
    finally:
        restored.close()
    return checkpoint_payload


def main():
    parser=argparse.ArgumentParser(description="Train real BEAN SpongeTD on native EZ-FEA measurements")
    parser.add_argument("dataset",help="Full actual EZ-FEA native_curriculum.json")
    parser.add_argument("--out",default="runs/bean_real_fea_learning")
    args=parser.parse_args()
    report=learn_from_native_dataset(json.loads(Path(args.dataset).read_text()),args.out)
    print(json.dumps({
        "real_training_cases":report["training_real_native_cases"],
        "unseen_geometry_cases":report["heldout_geometry_distinct_cases"],
        "durable_real_q_updates":report["training_q_updates"],
        "heldout_mean_baseline_relative_error":report["heldout"]["overall"]["analytical_mean_relative_error"],
        "heldout_mean_bean_relative_error":report["heldout"]["overall"]["bean_mean_relative_error"],
        "holdout_improvement_percentage_points":report["heldout"]["overall"]["relative_error_improvement_percentage_points"],
        "checkpoint_promotable":report["checkpoint"]["promotable"],
        "engineering_validation":"not_established",
    },indent=2))


if __name__=="__main__":
    main()

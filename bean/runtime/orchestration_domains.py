"""Native domain tools for the Core orchestrator.

Revision 2026-11-23: connect existing engineering, physics, SketchLab,
world model and simulated embodiment to the same GoalCycle. No second
model, network service or real actuator is introduced.
"""
from __future__ import annotations

import json
from pathlib import Path


def register_domain_tools(orchestrator, *, body_state, motion_safety, simulator,
                          model_store, artifact_root):
    """Register actual Core operations; import optional drawing only on use."""
    from bean.engineering.jobsite import evaluate_request
    from bean.engineering.stress_solver import solve_stress_reference
    from bean.engineering.spaceflight import solve_spaceflight_reference
    from bean.engineering.fea_evidence import crosscheck_native_torsion
    from bean.motion.command import MotionCommand, CommandIntent

    root = Path(artifact_root).expanduser().resolve()

    def jobsite(args, task_ref):
        return evaluate_request({**args, "schema": "bean.jobsite_request.v1"})

    def stress(args, task_ref):
        return solve_stress_reference({**args, "schema": "bean.stress_request.v1"})

    def spaceflight(args, task_ref):
        return solve_spaceflight_reference(
            {**args, "schema": "bean.spaceflight_request.v1"})

    def fea(args, task_ref):
        return crosscheck_native_torsion(args["report"],
                                         source_ref=args.get("source_ref"))

    def world(args, task_ref):
        return {"claims": model_store.snapshot(), "source": "native_world_model"}

    def observe_body(args, task_ref):
        return {"body": body_state.snapshot(),
                "source": "native_body_state", "physical_sensor_verified": False}

    def motion(args, task_ref):
        # Existing simulator only. Use the same state and motion checks as Core.
        before = body_state.get_joint(args["joint_id"])
        command = MotionCommand(
            joint_id=args["joint_id"], intent=CommandIntent(args.get("intent", "move_to")),
            target_pos=float(args.get("target_pos", 0)),
            speed=float(args["speed"]), notes="Native orchestration " + task_ref)
        verdict = motion_safety.check(command, current_pos=before.position)
        result = simulator.execute(command, verdict,
                                   session_uuid=orchestrator.session_uuid)
        return {"status": "success" if result.success else "failed",
                "joint_id": command.joint_id, "before": before.position,
                "after": result.new_position, "violations": verdict.violations,
                "outcome": result.outcome.value, "simulated": True,
                "physical_motion_executed": False, "sensor_verified": False}

    def draw(args, task_ref):
        from bean.creativity.sketch_lab import SketchLab
        out = root / "draw" / task_ref
        report = SketchLab(orchestrator.core).run(
            task_ref=task_ref, output_dir=out, subject=args.get("subject"),
            max_attempts=args.get("attempts", 2), backend="stdlib",
            allow_online=False, require_live=True)
        manifest = json.loads((out / "run.json").read_text(encoding="utf-8"))
        successful = [item for item in report["history"] if item.get("sha256")]
        selected = next((item for item in successful
                         if item["attempt"] == manifest.get("selected_attempt")), None)
        return {"status": "success" if successful else "failed",
                "subject": report["subject"], "attempts": report["attempts"],
                "artifacts": successful, "selected": selected,
                "receipt": report["run_receipt"],
                "visual_success_independently_verified": False}

    orchestrator.register("engineering_jobsite",
        "Construction math. wall_studs: {operation,length_ft,spacing_in}; "
        "wall_layout: add openings; beam_check: {operation,members,project_defaults}. "
        "Use supplied dimensions and limits.", jobsite)
    orchestrator.register("shaft_stress",
        "Closed-form shaft mechanics: {geometry:{shape:solid_circular_shaft,radius_mm},"
        "loads:{axial_force_n,bending_moment_y_nmm,bending_moment_z_nmm,torque_x_nmm},"
        "point_mm:[y,z]}", stress)
    orchestrator.register("spaceflight_physics",
        "Physics: {calculation,parameters}. orbit {body,altitude_km}; hohmann "
        "{mu_km3_s2,start_radius_km,end_radius_km}; mars_transfer {}; rocket "
        "{delta_v_km_s,isp_s,dry_mass_kg}; departure_burn "
        "{body,parking_altitude_km,v_infinity_km_s}; acceleration "
        "{delta_v_km_s,acceleration_m_s2}; earth_projectile "
        "{launch_speed_m_s,angle_deg,initial_height_m,gravity_m_s2,linear_drag_s_inv}; "
        "two_body_propagation {body,position_km,velocity_km_s,step_seconds,steps}.",
        spaceflight)
    orchestrator.register("fea_review",
        "Crosscheck supplied EZ-FEA circular shaft torsion evidence: {report,source_ref?}",
        fea)
    orchestrator.register("world_state", "Read stored world-model claims: {}", world)
    orchestrator.register("body_state", "Read joint IDs and native body state: {}", observe_body)
    orchestrator.register("simulate_joint",
        "Simulate one joint command, no physical actuation: "
        "{joint_id,intent:move_to|move_by|hold|neutral,target_pos,speed}. "
        "Read body_state first when joint IDs are unknown.", motion)
    orchestrator.register("draw",
        "Use existing live Core model to create original SVG drawings: "
        "{subject?:str,attempts?:int}. Returns saved artifact paths and hashes.", draw)

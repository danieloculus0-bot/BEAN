"""Cross-domain, nonlinear BEAN principle-transfer benchmark.

Source: quality-system maintenance and cascading production defects.
Target: ecosystem recovery with thresholded reproduction and food-web effects.

Different state/action descriptions and nonlinear dynamics share only five
explicitly mapped decision concepts. BEAN evaluates six predeclared selection
policies on source training cases and RETAINS the measured winner in the
existing SHA-chain ExperienceBank. It then applies that retained policy to
unseen target cases without target teaching/reward access before selection.

Measure blind target utility versus urgency-first, random, and shuffled-memory
controls. Results are simulation evidence, not external observations.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import random
import statistics

from bean.learning.experimental import ExperienceBank
from bean.optimization.autodev import canonical

SCHEMA = "bean.abstract_nonlinear_transfer.v1"
POLICIES = ("urgent", "upstream", "balanced", "cost_aware",
            "threshold", "risk_aware")
TRAIN_SEEDS = tuple(range(800, 832))
BLIND_SEEDS = tuple(range(10000, 10080))
HORIZON = 4


def clip(x):
    return min(1.0, max(0.0, float(x)))


def make_shop(seed):
    rng = random.Random(seed)
    n = 6
    return {
        "plant": "assembly-and-inspection",
        "stations": [{
            "wear": rng.uniform(.18, .79),
            "scrap_exposure": rng.uniform(.45, 1.3),
            "repair_cost": rng.uniform(.25, .88),
            "variance": rng.uniform(.05, .35),
        } for _ in range(n)],
        "routing": [(i, j, rng.uniform(.45, 1.0))
                    for i in range(n) for j in range(i+1, n)
                    if j == i+1 or (j == i+2 and rng.random() < .72)],
        "temperature": rng.uniform(.1, .5),
    }


def make_ecosystem(seed):
    rng = random.Random(seed)
    n = 7
    return {
        "reserve": "watershed-and-pollination",
        "guilds": [{
            "abundance": rng.uniform(.12, .75),
            "service": rng.uniform(.45, 1.3),
            "intervention_cost": rng.uniform(.25, .85),
            "climate_exposure": rng.uniform(.05, .55),
        } for _ in range(n)],
        "food_web": [(i, j, rng.uniform(.35, .95))
                     for i in range(n) for j in range(i+1, n)
                     if j == i+1 or (j == i+2 and rng.random() < .65)],
        "weather": [rng.uniform(-.17, .08) for _ in range(HORIZON)],
    }


def make_ideas(seed):
    """Portfolio with global innovation milestones, not a dependency graph."""
    rng = random.Random(seed)
    n = 9
    return {
        "laboratory": "research-portfolio",
        "experiments": [{
            "readiness": rng.uniform(.16, .79),
            "potential": rng.uniform(.45, 1.35),
            "funding": rng.uniform(.26, .89),
            "failure_rate": rng.uniform(.06, .43),
            "discipline": i % 3,
        } for i in range(n)],
        "funding_climate": [rng.uniform(-.10, .045)
                            for _ in range(HORIZON)],
        "milestone": rng.uniform(.55, .68),
    }


def ideas_features(world):
    projects = world["experiments"]
    milestone = world["milestone"]
    maxima = [max(x["readiness"] for x in projects
                  if x["discipline"] == field) for field in range(3)]
    result = []
    for i, project in enumerate(projects):
        current = project["readiness"]
        gap = 1-current
        discipline = project["discipline"]
        shortfall = max(0, milestone-maxima[discipline])
        # Abstract portfolio leverage arises from a coverage shortfall in a
        # unique knowledge discipline, not network causality.
        other_covered = sum(maxima[j] >= milestone for j in range(3)
                            if j != discipline)
        result.append({
            "id": i,
            "need": clip(gap*project["potential"]),
            "leverage": clip(gap*(shortfall+.15)*(1+.25*other_covered)*1.25),
            "cost": clip(project["funding"]),
            "uncertainty": clip(project["failure_rate"]),
            "near_tip": clip(1-abs(current-milestone)*1.7),
        })
    return result


def ideas_utility(world):
    projects = world["experiments"]
    base = sum(x["potential"]*x["readiness"]**1.8 for x in projects)
    best = [max(x["readiness"] for x in projects if
                x["discipline"] == field) for field in range(3)]
    # Reward emerges nonlinearly from *portfolio-level* combination of
    # independent disciplines, including a sharp threshold.
    synergy = 18*math.prod(best)**2
    breakthrough = 10 if all(x >= world["milestone"] for x in best) else 0
    return 3*base + synergy + breakthrough


def ideas_step(world, action, stage):
    projects = world["experiments"]
    project = projects[action]
    project["readiness"] = clip(
        project["readiness"] + .36*(1-project["readiness"]))
    fee = project["funding"]*1.2
    climate = world["funding_climate"][stage]
    for p in projects:
        p["readiness"] = clip(p["readiness"]
                               - .012*p["failure_rate"]
                               + climate*p["failure_rate"]*.18)
    return fee


def shop_features(world):
    stations = world["stations"]
    score = []
    for i, a in enumerate(stations):
        wear = a["wear"]
        exposure = a["scrap_exposure"]
        reach = sum(
            w * stations[j]["scrap_exposure"] * stations[j]["wear"]
            for source, j, w in world["routing"] if source == i)
        score.append({
            "id": i,
            "need": clip(wear * exposure),
            "leverage": clip(wear * (reach / 2.0)),
            "cost": clip(a["repair_cost"]),
            "uncertainty": clip(a["variance"] * (1 + world["temperature"])),
            "near_tip": clip(max(0, wear - .4) * 1.7),
        })
    return score


def ecosystem_features(world):
    guilds = world["guilds"]
    score = []
    for i, a in enumerate(guilds):
        lack = 1-a["abundance"]
        network = sum(
            w * guilds[j]["service"] * (1-guilds[j]["abundance"])
            for source, j, w in world["food_web"] if source == i)
        score.append({
            "id": i,
            "need": clip(lack * a["service"]),
            "leverage": clip(lack * network / 1.9),
            "cost": clip(a["intervention_cost"]),
            "uncertainty": clip(a["climate_exposure"]),
            "near_tip": clip(max(0, .63-a["abundance"]) * 1.8),
        })
    return score


def score_action(arm, f):
    x, y = f["need"], f["leverage"]
    c, u, t = f["cost"], f["uncertainty"], f["near_tip"]
    if arm == "urgent":
        return x
    if arm == "upstream":
        return y + .12*x - .18*c
    if arm == "balanced":
        return .58*x + .77*y - .16*c
    if arm == "cost_aware":
        return (x+.36*y) / (.4+c)
    if arm == "threshold":
        return .15*x + 1.1*y + .42*t*y - .18*c
    if arm == "risk_aware":
        return .45*x + .87*y - .51*u - .23*c
    raise ValueError("Unknown candidate policy")


def choose(arm, frames):
    if arm == "random":
        raise ValueError("Use independently seeded random baseline")
    # Tie-break doesn't use a target answer or a future outcome.
    return max(frames, key=lambda f: (score_action(arm, f), -f["id"]))["id"]


def shop_utility(world):
    stations = world["stations"]
    loss = sum(a["scrap_exposure"] * a["wear"]**2 for a in stations)
    cascades = sum(
        w * max(0, stations[i]["wear"] + stations[j]["wear"] - .8)**2
        for i, j, w in world["routing"])
    # Throughput is an interacting, thresholded nonlinear objective.
    return 100/(1+loss+1.5*cascades+3.0*max(0, cascades-1.1)**2)


def ecosystem_utility(world):
    guilds = world["guilds"]
    base = sum(a["service"] * a["abundance"]**1.65 for a in guilds)
    interactions = sum(
        w * (guilds[i]["abundance"]*guilds[j]["abundance"])**2
        for i, j, w in world["food_web"])
    tip_penalty = sum(
        max(0, .40-a["abundance"])**2 * a["service"]
        for a in guilds)
    return 5*base + 9*interactions - 13*tip_penalty


def shop_step(world, action):
    stations = world["stations"]
    repaired = stations[action]
    repaired["wear"] *= .39
    fee = repaired["repair_cost"] * .85
    before = [a["wear"] for a in stations]
    for i, a in enumerate(stations):
        upstream = sum(
            w * before[source]**2 for source, target, w in world["routing"]
            if target == i)
        a["wear"] = clip(a["wear"] + .027 + .13*upstream)
    return fee


def ecosystem_step(world, action, stage):
    guilds = world["guilds"]
    intervention = guilds[action]
    intervention["abundance"] = clip(
        intervention["abundance"] + .36*(1-intervention["abundance"]))
    fee = intervention["intervention_cost"] * 1.35
    previous = [a["abundance"] for a in guilds]
    weather = world["weather"][stage]
    for i, a in enumerate(guilds):
        ancestors = [(s, w) for s, t, w in world["food_web"] if t == i]
        dependency = sum(w*(previous[s]-.53) for s, w in ancestors)
        # Thresholded enabling vs suppression and climate/weather interaction.
        support = (max(0, dependency)**1.5
                   - 1.25*max(0, -dependency)**1.4)
        local = (.054*previous[i]*(1-previous[i])
                 + .18*support
                 - a["climate_exposure"] * max(0, -weather)*.53)
        a["abundance"] = clip(previous[i] + local + weather*.22)
    return fee


def rollout(kind, seed, arm):
    factories = {"shop": make_shop, "ecosystem": make_ecosystem,
                 "ideas": make_ideas}
    if kind not in factories:
        raise ValueError("Unknown transfer task")
    world = factories[kind](seed)
    total = 0.
    chosen = []
    rng = random.Random(seed ^ 0x5A17)
    for stage in range(HORIZON):
        frames = (shop_features(world) if kind == "shop" else
                  ecosystem_features(world) if kind == "ecosystem"
                  else ideas_features(world))
        action = rng.choice(frames)["id"] if arm == "random" else choose(arm, frames)
        chosen.append(action)
        fee = (shop_step(world, action) if kind == "shop" else
               ecosystem_step(world, action, stage) if kind == "ecosystem"
               else ideas_step(world, action, stage))
        utility = (shop_utility(world) if kind == "shop" else
                   ecosystem_utility(world) if kind == "ecosystem"
                   else ideas_utility(world))
        total += utility / HORIZON - fee
    return {"utility": round(total, 8), "actions": chosen}


def compare(kind, seeds):
    rows = []
    for seed in seeds:
        scores = {arm: rollout(kind, seed, arm)["utility"]
                  for arm in (*POLICIES, "random")}
        rows.append({"case": str(seed), "rewards": scores})
    return rows


def means(rows):
    arms = rows[0]["rewards"]
    return {arm: round(statistics.mean(r["rewards"][arm] for r in rows), 6)
            for arm in arms}


def learn_principle(bank, source_rows, dataset="shop-training-v1"):
    if len(source_rows) < 16 or len({r["case"] for r in source_rows}) != len(source_rows):
        raise ValueError("Source training needs distinct independently simulated cases")
    if any(set(r["rewards"]) != {*POLICIES, "random"} for r in source_rows):
        raise ValueError("Source reward comparison is incomplete")
    score = means(source_rows)
    winner = max(POLICIES, key=lambda a: (score[a], -POLICIES.index(a)))
    receipt = {
        "schema": "bean.adaptive_lab026.v1",
        "experiment": SCHEMA,
        "phase": "source_selection",
        "source_domain": "quality_maintenance",
        "source_dataset_id": dataset,
        "source_cases": len(source_rows),
        "source_mean_utility": score,
        "measured_selected_policy": winner,
        "source_question_receipt_sha256": sha256(canonical(source_rows)).hexdigest(),
        "source_feedback_origin": "deterministic_simulator",
        "target_feedback_available_at_selection": False,
        "autonomous_policy_search": "finite_six_candidate_empirical_selection",
        "external_validation": False,
        "action_authorization": False,
    }
    receipt["receipt_hash"] = sha256(canonical(receipt)).hexdigest()
    bank.record_trial(receipt)
    return receipt


def recover_principle(bank, source_dataset_id="shop-training-v1"):
    records = [e["data"] for e in bank.journal.events()
               if e["kind"] == "trial"
               and e["data"].get("experiment") == SCHEMA
               and e["data"].get("phase") == "source_selection"
               and e["data"].get("source_dataset_id") == source_dataset_id]
    if len(records) != 1:
        raise ValueError("Exactly one retained source selection required")
    data = records[0]
    check = dict(data)
    receipt = check.pop("receipt_hash", None)
    if receipt != sha256(canonical(check)).hexdigest():
        raise ValueError("Source selection integrity failure")
    return data["measured_selected_policy"]


def run_experiment(database, *, source_seeds=TRAIN_SEEDS,
                   blind_seeds=BLIND_SEEDS, target_kind="ecosystem"):
    """Experiment order prevents hidden target information entering selection."""
    if target_kind not in ("ecosystem", "ideas"):
        raise ValueError("Expected a separately defined nonlinear target")
    if set(source_seeds) & set(blind_seeds):
        raise ValueError("Source and target seed IDs must be disjoint")
    if len(set(blind_seeds)) != len(blind_seeds) or len(blind_seeds) < 32:
        raise ValueError("Blind evaluation needs distinct previously unseen IDs")
    bank = ExperienceBank(database)
    try:
        source = compare("shop", source_seeds)
        selection = learn_principle(bank, source)
    finally:
        bank.close()

    # Recover from disk instead of reading the learner's in-memory winner.
    recovered = ExperienceBank(database)
    try:
        winner = recover_principle(recovered)
        initial = recovered.journal.export()
    finally:
        recovered.close()
    target = compare(target_kind, blind_seeds)
    control = means(target)
    target_arm = [row["rewards"][winner] for row in target]
    baseline = [row["rewards"]["urgent"] for row in target]
    random_base = [row["rewards"]["random"] for row in target]
    differences = [round(x-y, 8) for x,y in zip(target_arm,baseline)]
    report = {
        "schema": SCHEMA, "source_dataset": "shop-training-v1",
        "target_dataset": target_kind + "-blind-v1",
        "source_cases": len(source), "target_cases": len(target),
        "selected_source_policy": winner,
        "source_means": selection["source_mean_utility"],
        "target_means": control,
        "target_delta_vs_urgent": round(statistics.mean(differences), 6),
        "target_delta_vs_random": round(
            statistics.mean(x-y for x,y in zip(target_arm, random_base)), 6),
        "target_wins_vs_urgent": sum(a>b for a,b in zip(target_arm, baseline)),
        "target_losses_vs_urgent": sum(a<b for a,b in zip(target_arm, baseline)),
        "target_ties_vs_urgent": sum(a==b for a,b in zip(target_arm, baseline)),
        "target_case_deltas": differences,
        "learned_policy_recovered_from_owned_journal": True,
        "pre_target_ledger_tip": initial["tip"],
        "target_feedback_used_in_selection": False,
        "domain_adapter_mapping_provided": True,
        "independent_real_world_evaluation": False,
    }
    report["report_sha256"] = sha256(canonical(report)).hexdigest()
    recovered = ExperienceBank(database)
    try:
        # A new observation, not an automatically trusted correction.
        recovered.record_trial({
            "schema": "bean.adaptive_lab026.v1",
            "experiment": SCHEMA, "phase": "blind_target_report",
            "target_dataset_id": target_kind + "-blind-v1",
            "report_sha256": report["report_sha256"],
            "reported_outcome": "heldout_simulation_only",
            "target_feedback_used_in_selection": False,
        })
        report["post_target_ledger_tip"] = recovered.journal.export()["tip"]
    finally:
        recovered.close()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--target-kind", choices=("ecosystem", "ideas"),
                        default="ecosystem")
    opt = parser.parse_args(argv)
    report = run_experiment(opt.database, target_kind=opt.target_kind)
    raw = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if opt.output:
        opt.output.parent.mkdir(parents=True, exist_ok=True)
        opt.output.write_text(raw, encoding="utf-8")
    print("BEAN_ABSTRACT_NONLINEAR_TRANSFER " + json.dumps({
        k:v for k,v in report.items() if k not in
        ("target_case_deltas", "source_means", "target_means")
    }, sort_keys=True))
    print("TARGET_MEANS " + json.dumps(report["target_means"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

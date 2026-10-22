"""Lab027: train BEAN SpongeTD on procedural puzzles; test unfamiliar maps.

Three disjoint splits. Frozen holdout. Source-native SHA-journal checkpoint.
The environment is synthetic and domain-limited, not general intelligence.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import random
import statistics
from pathlib import Path
from bean.optimization.sponge_td import SpongeTD
from bean.optimization.sponge_intuition import SpongeIntuition

SCHEMA = "bean.intuition.lab027.v1"
ACTIONS = ("up", "right", "down", "left")
MOVES = ((0, -1), (1, 0), (0, 1), (-1, 0))
CANDIDATES = tuple((p, b) for p in (0., .02, .06, .12, .25, .5)
                   for b in (0., .05, .2))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class KeyDoor:
    """Random solvable grid; agent needs a key before the exit."""

    def __init__(self, seed):
        rng = random.Random(seed)
        self.seed = seed
        for _ in range(500):
            n = rng.randint(5, 8)
            walls = {(x, y) for x in range(n) for y in range(n)
                     if rng.random() < rng.uniform(.10, .24)}
            free = [(x, y) for x in range(n) for y in range(n)
                    if (x, y) not in walls]
            if len(free) < n*n*.6:
                continue
            start, key, exit_ = rng.sample(free, 3)

            def connected(a, b):
                queue, seen = [a], {a}
                for point in queue:
                    if point == b:
                        return True
                    for vx, vy in MOVES:
                        q = (point[0]+vx, point[1]+vy)
                        if (q not in walls and 0 <= q[0] < n
                                and 0 <= q[1] < n and q not in seen):
                            seen.add(q)
                            queue.append(q)
                return False

            d1 = abs(start[0]-key[0])+abs(start[1]-key[1])
            d2 = abs(key[0]-exit_[0])+abs(key[1]-exit_[1])
            if connected(start, key) and connected(key, exit_) and d1 >= 2 and d2 >= 2:
                break
        else:
            raise RuntimeError("Could not generate solvable task")
        self.n, self.walls = n, walls
        self.start, self.key, self.exit = start, key, exit_
        self.pos, self.has_key, self.done, self.steps = start, False, False, 0
        self.max_steps = 4*n*n

    def free(self, pos):
        return 0 <= pos[0] < self.n and 0 <= pos[1] < self.n and pos not in self.walls

    def obs(self):
        goal = self.exit if self.has_key else self.key
        dx, dy = goal[0]-self.pos[0], goal[1]-self.pos[1]
        return ("keydoor-v1", int(self.has_key),
                (dx > 0)-(dx < 0), (dy > 0)-(dy < 0),
                min(abs(dx)+abs(dy), 6),
                *(int(not self.free((self.pos[0]+vx, self.pos[1]+vy)))
                  for vx, vy in MOVES))

    def destinations(self):
        options = {}
        for action, (dx, dy) in enumerate(MOVES):
            dest = (self.pos[0]+dx, self.pos[1]+dy)
            if self.free(dest):
                options[action] = dest
        return options

    def move(self, action):
        if self.done or type(action) is not int or action not in range(4):
            raise ValueError("Invalid move")
        goal = self.exit if self.has_key else self.key
        before = abs(goal[0]-self.pos[0])+abs(goal[1]-self.pos[1])
        self.steps += 1
        dx, dy = MOVES[action]
        dest = (self.pos[0]+dx, self.pos[1]+dy)
        blocked = not self.free(dest)
        if not blocked:
            self.pos = dest
        after = abs(goal[0]-self.pos[0])+abs(goal[1]-self.pos[1])
        reward = -.03-(.2 if blocked else 0)
        reward += .065 if after < before else -.065 if after > before else 0
        if self.pos == self.key and not self.has_key:
            self.has_key = True
            reward += 2.
        if self.pos == self.exit and self.has_key:
            self.done = True
            reward += 6.
        self.done = self.done or self.steps >= self.max_steps
        return reward, self.done


def split(phase, count):
    if type(count) is not int or not 2 <= count <= 10000:
        raise ValueError("2..10000 tasks required")
    base, delta = {"train": (100000, 67), "validation": (400000, 71),
                   "holdout": (800000, 59)}[phase]
    return [base+i*delta for i in range(count)]


def train(policy, seeds, events):
    for index, seed in enumerate(seeds):
        env = KeyDoor(seed)
        epsilon = max(.045, .70*(1-index/len(seeds))**2)
        while not env.done:
            state = env.obs()
            q = policy.values(state)
            if policy.rng.random() < epsilon:
                action = policy.rng.randrange(len(ACTIONS))
            else:
                best = max(q)
                action = policy.rng.choice([i for i, v in enumerate(q) if v == best])
            reward, done = env.move(action)
            policy.learn(state, action, reward, env.obs(), done)
        events.append({"phase": "train", "arm": "SpongeTD", "seed": seed,
                       "passed": env.pos == env.exit and env.has_key,
                       "steps": env.steps, "epsilon": round(epsilon, 7)})


def evaluate(policy, seeds, *, phase, arm, penalty, revisit, events):
    original_hash = sha(policy.q)
    results = []
    for seed in seeds:
        env = KeyDoor(seed)
        controller = SpongeIntuition(
            policy, seed=seed+345235, visit_penalty=penalty,
            revisit_penalty=revisit, lookback=10)
        while not env.done:
            available = env.destinations()
            action = controller.choose(
                env.obs(), location_ref=env.pos,
                legal_actions=list(available) or list(range(4)),
                candidate_destinations=available)
            env.move(action)
        row = {"phase": phase, "arm": arm, "seed": seed,
               "passed": bool(env.pos == env.exit and env.has_key),
               "steps": env.steps}
        events.append(row)
        results.append(row)
    if sha(policy.q) != original_hash:
        raise AssertionError("Evaluation modified learned Q-values")
    return results


def metrics(rows):
    return {"count": len(rows), "solved": sum(row["passed"] for row in rows),
            "success_rate": round(sum(row["passed"] for row in rows)/len(rows), 6),
            "mean_steps": round(statistics.mean(row["steps"] for row in rows), 4)}


def utility(rows):
    m = metrics(rows)
    return round(100*m["success_rate"]-m["mean_steps"]/8, 6)


def bootstrap(cold, trained):
    if [x["seed"] for x in cold] != [x["seed"] for x in trained]:
        raise ValueError("Unmatched holdout seeds")
    differences = [a["steps"]-b["steps"] for a, b in zip(cold, trained)]
    rng = random.Random(1729)
    samples = [statistics.mean(differences[rng.randrange(len(differences))]
                               for _ in differences) for _ in range(2000)]
    samples.sort()
    return {"mean_steps_saved": round(statistics.mean(differences), 4),
            "paired_bootstrap_95pct_ci": [round(samples[50], 4),
                                         round(samples[1950], 4)]}


def write_events(directory, events, report):
    payload = b"".join(canonical(x)+b"\n" for x in events)
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buf, mode="wb",
                       mtime=0, compresslevel=9) as f:
        f.write(payload)
    compressed = buf.getvalue()
    if gzip.decompress(compressed) != payload:
        raise AssertionError("Lossless event recovery failed")
    (directory/"events.jsonl.gz").write_bytes(compressed)
    report["ledger"] = {
        "rows": len(events), "sha256_raw": hashlib.sha256(payload).hexdigest(),
        "sha256_gzip": hashlib.sha256(compressed).hexdigest(),
        "raw_bytes": len(payload), "compressed_bytes": len(compressed),
        "lossless_roundtrip": True}
    (directory/"scoreboard.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def run(output, *, training=3000, validation=180, holdout=240):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    train_ids = split("train", training)
    val_ids = split("validation", validation)
    held_ids = split("holdout", holdout)
    if not (set(train_ids).isdisjoint(val_ids)
            and set(val_ids).isdisjoint(held_ids)
            and set(train_ids).isdisjoint(held_ids)):
        raise AssertionError("Data split overlap")
    manifest = {
        "train_sha256": sha(train_ids), "validation_sha256": sha(val_ids),
        "holdout_sha256": sha(held_ids),
        "train_count": len(train_ids), "validation_count": len(val_ids),
        "holdout_count": len(held_ids),
        "candidate_params": [list(x) for x in CANDIDATES],
        "map_family": "procedural_solvable_keydoor_5_to_8",
        "source": "BEAN SpongeTD + SpongeIntuition",
    }
    events = []
    args = dict(actions=ACTIONS, alpha=.24, gamma=.96, epsilon=.1, seed=43)
    learner = SpongeTD(output/"policy.sqlite", **args)
    cold = SpongeTD(output/"cold.sqlite", **args)
    try:
        train(learner, train_ids, events)
        candidates = []
        for i, (penalty, revisit) in enumerate(CANDIDATES):
            part = evaluate(learner, val_ids, phase="validation",
                            arm=f"candidate-{i}", penalty=penalty,
                            revisit=revisit, events=events)
            candidates.append({"id": i, "visit_penalty": penalty,
                               "revisit_penalty": revisit, **metrics(part)})
        best = sorted(candidates, key=lambda x:
                      (-x["solved"], x["mean_steps"], x["id"]))[0]
        settings = (best["visit_penalty"], best["revisit_penalty"])
        cold_val = evaluate(cold, val_ids, phase="validation_control",
                            arm="cold_selected", penalty=settings[0],
                            revisit=settings[1], events=events)
        trained_val = [x for x in events if x["phase"] == "validation"
                       and x["arm"] == f"candidate-{best['id']}"]
        validation_receipt = sha({"manifest": manifest,
                                  "cold": cold_val, "trained": trained_val})
        prior_q_sha = sha(learner.q)
        checkpoint = learner.checkpoint(
            baseline=utility(cold_val), candidate=utility(trained_val),
            samples=len(val_ids), evaluation_sha256=validation_receipt)
        learner.close()
        learner = SpongeTD(output/"policy.sqlite", **args)
        if sha(learner.q) != prior_q_sha:
            raise AssertionError("SpongeTD checkpoint failed exact recovery")
        hold = {}
        for name, policy, config in [
            ("cold_plain", cold, (0., 0.)),
            ("trained_plain", learner, (0., 0.)),
            ("cold_intuition", cold, settings),
            ("trained_intuition", learner, settings),
        ]:
            hold[name] = evaluate(policy, held_ids, phase="holdout",
                                  arm=name, penalty=config[0],
                                  revisit=config[1], events=events)
        all_train = [x for x in events if x["phase"] == "train"]
        report = {
            "schema": SCHEMA,
            "status": "real_sponge_td_learning_on_synthetic_maps",
            "scope": "unseen_maps_within_one_puzzle_family_not_general_intelligence",
            "manifest": manifest,
            "training": {
                "full": metrics(all_train),
                "first_200": metrics(all_train[:200]),
                "last_200": metrics(all_train[-200:])},
            "policy": {"q_states": len(learner.q), "transitions": learner.steps,
                       "sha256": sha(learner.q), "checkpoint": checkpoint,
                       "exact_restart_verified": True},
            "selection": {
                "best": best, "candidates": candidates,
                "validation_cold": metrics(cold_val),
                "validation_trained": metrics(trained_val),
                "receipt_sha256": validation_receipt,
                "never_used_holdout_to_select": True},
            "holdout": {arm: metrics(rows) for arm, rows in hold.items()},
            "paired": bootstrap(hold["cold_intuition"], hold["trained_intuition"]),
            "limitations": [
                "Host-generated synthetic tasks, not cross-domain intelligence",
                "Encoded relative target and legal actions are provided to agents",
                "Novelty policy itself works without Q learning",
                "Holdout is frozen, no train or strategy tuning on held-out maps",
                "Report is an engineering test receipt, not independent peer review"],
        }
        write_events(output, events, report)
        readme = (
            "# BEAN Lab027 measured intuition\n\n"
            "Synthetic puzzle family, actual SpongeTD training, persisted SHA Q-policy.\n\n"
            "| Frozen holdout arm | Solved | Mean moves |\\n|---|---:|---:|\\n"
            + "".join(
                f"| {arm} | {report['holdout'][arm]['solved']}/{holdout}"
                f" | {report['holdout'][arm]['mean_steps']:.1f} |\\n"
                for arm in ("cold_plain", "trained_plain",
                            "cold_intuition", "trained_intuition"))
            + "\nSource event history is losslessly compressed in events.jsonl.gz.\n"
              "Selection used validation only; the holdout was kept separate.\n")
        (output/"SCOREBOARD.md").write_text(readme, encoding="utf-8")
        return report
    finally:
        learner.close()
        cold.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="lab027-results")
    p.add_argument("--training", type=int, default=3000)
    p.add_argument("--validation", type=int, default=180)
    p.add_argument("--holdout", type=int, default=240)
    a = p.parse_args()
    result = run(a.output, training=a.training,
                 validation=a.validation, holdout=a.holdout)
    print(json.dumps({
        "holdout": result["holdout"],
        "selection": result["selection"]["best"],
        "paired": result["paired"], "ledger": result["ledger"],
        "policy": {"q_states": result["policy"]["q_states"],
                   "exact_restart_verified": result["policy"]["exact_restart_verified"]},
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

"""BEAN research: visible, source-linked scoreboards and single-credit RL rewards.

Archives and source receipts remain authoritative. Scoreboards are convenient
summaries, not truth or intelligence claims. This module never starts a learner.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

VERSION = "bean.reward_context.v1"
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,127}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _brief(path: Path, root: Path) -> dict:
    raw = path.read_bytes()
    doc = json.loads(raw)
    if not isinstance(doc, dict) or not isinstance(doc.get("schema"), str):
        raise ValueError(f"invalid scoreboard: {path}")
    schema = doc["schema"]
    entry = {"id": path.relative_to(root).as_posix(), "schema": schema,
             "sha256": _sha(raw), "evidence_class": "historical_research_snapshot"}
    if schema == "bean.scoreboard.experimental.v1":
        entry["metrics"] = {
            "passes": doc.get("passes_total"), "tests_passed": doc.get("tests_passed"),
            "tests_failed": doc.get("tests_failed"), "policy_utility": doc.get("policy_utility"),
            "fast_baseline_utility": doc.get("fast_baseline_utility")}
        entry["meaning"] = "synthetic deterministic repeatability, not neural learning"
    elif schema == "bean.core.matrix.scoreboard.v1":
        entry["metrics"] = {"successful_jobs": doc.get("successful_jobs"),
                            "matrix_jobs": doc.get("matrix_jobs"),
                            "passed_assertions_summed": doc.get("passed_assertions_summed"),
                            "skips_summed": doc.get("skips_summed")}
        entry["meaning"] = "repeatability CI, not evidence of policy improvement"
        entry["source_revision"] = doc.get("source_commit")
    elif schema == "bean.lab009.scoring.v1":
        score = doc.get("score", {})
        entry["metrics"] = {key: score.get(key) for key in
                            ("baseline_correct", "frozen_post_restart_correct",
                             "online_post_investigation_correct", "total_cases")}
        entry["meaning"] = "synthetic frozen knowledge versus online acquisition"
        entry["source_revision"] = doc.get("source_commit")
    else:
        entry["meaning"] = "unrecognized scoreboard schema: metadata only"
        entry["metrics"] = {}
    return entry


def scoreboard_context(root: str | Path, *, max_entries: int = 20) -> dict:
    """Small, machine-readable context for an agent prompt or reward policy.

    Only read exact local scoreboard filenames, never infer nonexistent tests.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    if not 1 <= max_entries <= 100:
        raise ValueError("max_entries outside 1..100")
    paths = sorted(p for p in root.rglob("*scoreboard*.json") if p.is_file())
    selected = paths[:max_entries]
    items = [_brief(p, root) for p in selected]
    return {
        "schema": VERSION,
        "source": str(root),
        "entries": items,
        "entries_total": len(paths),
        "entries_omitted": len(paths)-len(items),
        "agent_note": ("These summaries are historical, not a live model score. "
                       "Retrieve immutable event/archive receipts before interpreting a gain. "
                       "No automatic neural training or deployment is implied."),
        "reward_contract": ("Reward is signed matched improvement on one named metric, "
                            "never a composite intelligence score; duplicate evaluation "
                            "receipts must not reward a second time."),
    }


@dataclass(frozen=True)
class RewardTrial:
    experiment: str
    metric: str
    condition_id: str
    baseline_run: str
    candidate_run: str
    baseline: float
    candidate: float
    direction: str
    matched_cases: int
    expected_cases: int
    evaluation_sha256: str
    evidence_ref: str
    evidence_kind: str = "synthetic"

    def validate(self) -> None:
        for name in ("experiment","metric","condition_id","baseline_run","candidate_run"):
            value = getattr(self, name)
            if not isinstance(value, str) or not ID.fullmatch(value):
                raise ValueError(f"invalid {name}")
        if self.direction not in ("higher","lower"):
            raise ValueError("direction must be higher or lower")
        if self.evidence_kind not in ("synthetic","measured"):
            raise ValueError("unsupported evidence kind")
        for v in (self.baseline,self.candidate):
            if type(v) not in (int,float) or not math.isfinite(v):
                raise ValueError("invalid measurement")
        if (type(self.matched_cases) is not int or type(self.expected_cases) is not int
                or self.matched_cases < 0 or self.expected_cases < 1
                or self.matched_cases > self.expected_cases):
            raise ValueError("invalid case coverage")
        if not isinstance(self.evaluation_sha256,str) or not DIGEST.fullmatch(self.evaluation_sha256):
            raise ValueError("missing evaluation receipt hash")
        if (not isinstance(self.evidence_ref,str) or not self.evidence_ref.startswith("https://")
                or len(self.evidence_ref)>500):
            raise ValueError("missing source URL")


def score_reward(trial: RewardTrial) -> dict:
    """Signed [-1,1] comparable-outcome reward, not an evidence authenticator.

    Missing coverage or the same run receives NO reward event (None), not a zero
    pretending to represent a verified tie.
    """
    trial.validate()
    # Credit is keyed by the evaluation evidence, not the caller's chosen
    # run label. Reusing one evaluation receipt cannot mint fresh reward IDs.
    credit_key = {"experiment":trial.experiment,"metric":trial.metric,
                  "condition_id":trial.condition_id,
                  "evaluation_sha256":trial.evaluation_sha256}
    receipt_id = "R." + _sha(_json(credit_key))[:24]
    base = {"schema": VERSION, "receipt_id":receipt_id, "experiment":trial.experiment,
            "metric":trial.metric, "evaluation_sha256":trial.evaluation_sha256,
            "evidence_ref":trial.evidence_ref, "evidence_kind":trial.evidence_kind,
            "verified_evidence":False,
            "verification_note":"Only a caller-supplied receipt reference; source truth not authenticated"}
    if trial.baseline_run == trial.candidate_run:
        return {**base, "eligible":False, "reason":"same_run", "reward":None}
    if trial.matched_cases != trial.expected_cases:
        return {**base, "eligible":False, "reason":"incomplete_matched_coverage", "reward":None}
    delta = (trial.candidate-trial.baseline) * (1 if trial.direction=="higher" else -1)
    # Bounded relative change. 0 for an exact tie. A regression is negative.
    reward = max(-1.0,min(1.0,delta / max(abs(trial.baseline),abs(trial.candidate),1.0)))
    return {**base, "eligible":True, "reason":"matched_receipt_attested",
            "baseline":trial.baseline, "candidate":trial.candidate,
            "condition_id":trial.condition_id, "direction":trial.direction,
            "reward":round(reward,8), "improved": reward>0, "regressed":reward<0}


def record_reward(root: str | Path, trial: RewardTrial) -> dict:
    """Immutable individual receipt. Repeat submissions get zero *additional* credit."""
    result = score_reward(trial)
    if not result["eligible"]:
        return {**result, "new_reward":False}
    folder = Path(root).resolve() / "reward_receipts"
    folder.mkdir(parents=True,exist_ok=True)
    path = folder / f'{result["receipt_id"]}.json'
    content = _json({"trial":asdict(trial), "result":result}) + b"\n"
    try:
        with path.open("xb") as output:
            output.write(content)
            output.flush()
    except FileExistsError:
        if path.read_bytes() != content:
            raise ValueError("immutable receipt conflict")
        return {**result, "new_reward":False, "receipt_path":str(path),
                "reason":"already_recorded"}
    return {**result, "new_reward":True, "receipt_path":str(path)}


def apply_once(learner: object, recorded: dict, *, state: Any, action: int,
               next_state: Any, done: bool) -> bool:
    """Explicit experiment adapter, no automatic policy or training changes."""
    if not recorded.get("eligible") or not recorded.get("new_reward"):
        return False
    reward = recorded["reward"]
    method = getattr(learner,"observe",None) or getattr(learner,"learn",None)
    if method is None:
        raise TypeError("expected an existing DQN observe or TD learn method")
    method(state,action,reward,next_state,done)
    # In-process duplicate defense. Cross-process ingestion must go through
    # record_reward, which checks the immutable receipt file on disk.
    recorded["new_reward"] = False
    recorded["applied_to_learner"] = True
    return True


def main() -> int:
    parser=argparse.ArgumentParser(description="Show BEAN its persisted scoreboards")
    parser.add_argument("--ledger",type=Path,default=Path("research/persistent_ledger"))
    args=parser.parse_args()
    print(json.dumps(scoreboard_context(args.ledger),indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

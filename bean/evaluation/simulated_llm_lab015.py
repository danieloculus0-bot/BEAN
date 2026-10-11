"""BEAN Lab 015: offline simulated reasoning-provider diagnostic.

This is NOT a large language model, not an Ollama replacement and not
independent learning. It is a compact, transparent, deterministic Bayesian
policy that implements the SAME provider protocol as the real LLM adapter,
so investigation, feedback, restart, ablation and validation can be tested
without any GPU, Jetson, keys, network or downloaded weights.

Unlike the earlier scripted fixture, the policy parses the actual model
prompt (not privileged evaluator context) and derives a probe decision from
supervised reliability estimates. It never receives sealed ground truth.
"""
from __future__ import annotations

import json
from typing import Any

from bean.reasoning.llm_adapter import LLMAdapterBase


class SimulatedLLMAdapter(LLMAdapterBase):
    adapter_name = "simulated_llm_policy"
    model_name = "bayesian_evidence_policy_not_a_language_model"

    @staticmethod
    def _answer(verdict: str, refs: list[str], confidence: float) -> dict:
        return {"action": "answer", "tool": None, "verdict": verdict,
                "evidence_refs": refs, "confidence": confidence}

    @staticmethod
    def _probe(tool: str) -> dict:
        return {"action": "probe", "tool": tool, "verdict": None,
                "evidence_refs": [], "confidence": 0.0}

    def complete(self, prompt: str, context: dict | None = None) -> dict:
        """Read ONLY the public exam prompt. Ignore internal evaluator context.

        The hidden scenario's true_state is not supplied in prompt and cannot
        influence this function. Free-form document notes are data only.
        """
        try:
            if not isinstance(prompt, str):
                raise ValueError("prompt must be text")
            prefix = "EXAM_INPUT:\n"
            if prefix not in prompt:
                raise ValueError("missing exam packet")
            packet = json.loads(prompt.split(prefix, 1)[1])
            if not isinstance(packet, dict):
                raise ValueError("bad exam packet")
            evidence = packet["evidence"]
            tools = packet["allowed_tools"]
            lessons = packet["lessons"]
            if (not isinstance(evidence, list) or not isinstance(tools, list)
                    or not isinstance(lessons, dict)):
                raise ValueError("unexpected fields")
            if len(evidence) > 25 or len(tools) > 5:
                raise ValueError("oversized exam packet")

            # Ignore all free-form text, including prompt injection in notes.
            verified = [
                e for e in evidence if isinstance(e, dict)
                and e.get("quality") == "verified"
                and e.get("value") in ("nominal", "fault")
                and isinstance(e.get("ref_id"), str)
            ]
            verified_states = {e["value"] for e in verified}
            if len(verified_states) > 1:
                decision = self._answer("unknown", [], 0.2)
            elif verified:
                recent = verified[-1]
                decision = self._answer(recent["value"], [recent["ref_id"]], 0.95)
            else:
                dashboard = next(
                    (e for e in evidence if isinstance(e, dict)
                     and e.get("source") == "dashboard"
                     and e.get("quality") == "unverified"
                     and e.get("value") in ("nominal", "fault")
                     and isinstance(e.get("ref_id"), str)),
                    None,
                )
                unavailable = any(
                    isinstance(e, dict) and e.get("source") == "reference"
                    and e.get("quality") == "missing" for e in evidence
                )
                d = lessons.get("dashboard", {})
                r = lessons.get("reference", {})
                d_n = d.get("observations", 0)
                r_n = r.get("observations", 0)
                d_p = d.get("reliability", 2 / 3)
                r_p = r.get("reliability", 2 / 3)
                if not (type(d_n) is int and 0 <= d_n <= 100000
                        and type(r_n) is int and 0 <= r_n <= 100000
                        and type(d_p) in (int, float) and 0 <= d_p <= 1
                        and type(r_p) in (int, float) and 0 <= r_p <= 1):
                    raise ValueError("bad calibration summary")

                # A probe is justified only after independently labeled
                # supervisory feedback has calibrated BOTH source classes.
                should_investigate = (
                    dashboard is not None and not unavailable
                    and "inspect_reference" in tools and d_n >= 6 and r_n >= 6
                    and r_p >= 0.75 and r_p - d_p >= 0.12
                )
                if should_investigate:
                    decision = self._probe("inspect_reference")
                elif unavailable or dashboard is None:
                    decision = self._answer("unknown", [], 0.2)
                elif d_n >= 6 and d_p < 0.58:
                    # In absence of stronger evidence, resist both the
                    # unreliable dashboard and any text-based instruction.
                    decision = self._answer("unknown", [], 0.2)
                else:
                    # Untested control policy answers tentatively, so paired
                    # ablation can reveal whether feedback has value.
                    decision = self._answer(
                        dashboard["value"], [dashboard["ref_id"]], 0.45
                    )
            return {
                "ok": True,
                "raw_text": json.dumps(decision, sort_keys=True),
                "adapter_name": self.adapter_name,
                "model_name": self.model_name,
            }
        except (TypeError, ValueError, KeyError, AttributeError, OverflowError) as exc:
            # Never turn a provider error into fabricated verified evidence.
            return {
                "ok": False, "error": type(exc).__name__,
                "adapter_name": self.adapter_name, "model_name": self.model_name,
            }


def run_offline(*, seeds: tuple[int, ...] = (7, 19, 43),
                training: int = 80, holdout: int = 75) -> dict[str, Any]:
    """Paired holdouts with a fresh policy instance after every restart."""
    from bean.evaluation.investigation_lab014 import trial
    arms = ("trained_tools", "untrained_tools", "trained_no_tools")
    out = []
    for seed in seeds:
        measurements = {}
        for arm in arms:
            measurements[arm] = trial(
                seed, SimulatedLLMAdapter,
                train_count=training, holdout_count=holdout,
                learn=arm != "untrained_tools", tools=arm != "trained_no_tools",
            )
        out.append({"seed": seed, "arms": measurements})
    return {
        "lab": "BEAN_SIMULATED_LLM_015",
        "provider": SimulatedLLMAdapter.adapter_name,
        "is_real_llm": False,
        "weights_trained": False,
        "ground_truth_leaked_to_model": False,
        "training_feedback": "simulated_supervisor_only",
        "seeds": list(seeds),
        "training_per_arm": training,
        "holdout_per_arm": holdout,
        "trials": out,
        "aggregate": {
            key: round(sum(
                trial_result["arms"][arm]["holdout"][key]
                for trial_result in out
            ) / len(out), 4)
            for arm in arms for key in []
        },
        "limitations": [
            "Bayesian source selection policy, not an LLM or text understanding.",
            "Supervisor supplies feedback after each training decision.",
            "Case generator is public; the simulator is not a blind benchmark.",
            "No real model API, robot, Jetson, camera or production memory used.",
        ],
    }


def main(argv=None) -> int:
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Offline BEAN simulated LLM evaluation")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--train", type=int, default=80)
    parser.add_argument("--holdout", type=int, default=75)
    args = parser.parse_args(argv)
    report = run_offline(training=args.train, holdout=args.holdout)
    result = json.dumps(report, indent=2, sort_keys=True)
    print(result)
    if args.report:
        args.report.parent.mkdir(exist_ok=True, parents=True)
        args.report.write_text(result + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

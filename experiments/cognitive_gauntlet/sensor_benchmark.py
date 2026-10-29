"""Same-tick sensor trust versus frozen controls, with delayed label feedback."""
import gzip
import hashlib
import json
import random
from pathlib import Path
from .sensor_reliability import OnlineSensorTrust, SensorObservation

REGIMES = ("diverse", "adversarial", "weak", "source_swap", "rapid", "correlated")
ARMS = ("fixed_prior", "long_memory", "forgetful", "unweighted")


def benchmark(seeds=30, rounds=120, first_seed=5000):
    if not 1 <= seeds <= 100 or not 20 <= rounds <= 400 or first_seed < 5000:
        raise ValueError("invalid sample budget")
    cases = []
    for regime in REGIMES:
        for seed in range(first_seed, first_seed + seeds):
            rng = random.Random(seed * 43 + sum(map(ord, regime)) * 211)
            truth = rng.randrange(2)
            long_memory = OnlineSensorTrust()
            forgetful = OnlineSensorTrust(decay=.97)
            for t in range(rounds):
                if regime == "rapid" and t:
                    truth ^= 1
                elif t and rng.random() < .08:
                    truth ^= 1
                profiles = {
                    "diverse": (.9, .85, .8, .7, .65),
                    "adversarial": (.9, .8, .72, .25, .08),
                    "weak": (.55, .54, .52, .51, .5),
                    "source_swap": ((.88, .82, .78, .25, .12) if t < rounds//2
                                    else (.12, .25, .28, .82, .9)),
                    "rapid": (.93, .82, .74, .4, .12),
                    "correlated": (.85, .85, .85, .3, .2),
                }
                shared = rng.random() < .85 if regime == "correlated" else None
                observations = []
                for i, p in enumerate(profiles[regime]):
                    good = shared if shared is not None and i < 3 else rng.random() < p
                    observations.append(SensorObservation(f"{regime}:{seed}:{t}:{i}",
                                                           f"s{i}", truth if good else 1-truth))
                fixed = OnlineSensorTrust()
                predictions = {
                    "fixed_prior": fixed.forecast(observations),
                    "long_memory": long_memory.forecast(observations),
                    "forgetful": forgetful.forecast(observations),
                    "unweighted": sum(o.value for o in observations) / len(observations),
                }
                losses = {k: (v-truth)**2 for k, v in predictions.items()}
                cases.append({"regime": regime, "seed": seed, "step": t,
                              "evidence": [o.__dict__ for o in observations],
                              "predictions": predictions, "losses": losses,
                              "trust_before_feedback": {o.origin: forgetful.reliability(o.origin)
                                                        for o in observations},
                              "revealed_outcome": truth})
                for model in (fixed, long_memory, forgetful):
                    model.learn(truth)
    scores = {}
    for regime in (*REGIMES, "all"):
        rows = [x for x in cases if regime == "all" or x["regime"] == regime]
        scores[regime] = {"n": len(rows), "mse": {
            arm: sum(x["losses"][arm] for x in rows)/len(rows) for arm in ARMS}}
    report = {"schema": "bean.gauntlet.sensor_feedback.v1", "seeds": seeds,
              "rounds": rounds, "first_seed": first_seed, "cases": cases,
              "scores": scores, "external_runtimes_executed": [],
              "outcome_delivered_after_each_prediction": True,
              "interpretation": "synthetic host-verified feedback; no external AGI"}
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["digest"] = hashlib.sha256(payload.encode()).hexdigest()
    return report


def main():
    report = benchmark()
    path = Path("cognitive-gauntlet-results/sensor-feedback.json.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, sort_keys=True) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0))
    assert gzip.decompress(path.read_bytes()) == raw
    print(json.dumps({"scores": report["scores"], "digest": report["digest"]}, indent=2))


if __name__ == "__main__":
    main()

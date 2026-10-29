"""Bounded evidence aggregation experiment with deterministic paired comparisons."""
import json
import random


def score(seed=7, rounds=200):
    rng = random.Random(seed)
    latest_error = 0.0
    pooled_error = 0.0
    cases = []
    for episode in range(rounds):
        truth = rng.randrange(2)
        observations = [float(truth if rng.random() < .75 else 1 - truth)
                        for _ in range(5)]
        latest = observations[-1]
        aggregate = sum(observations) / len(observations)
        a = (aggregate - truth) ** 2
        b = (latest - truth) ** 2
        pooled_error += a
        latest_error += b
        cases.append({"episode": episode, "truth": truth,
                      "observations": observations,
                      "pooled_error": a, "latest_error": b})
    return {"schema": "bean.cognitive_gauntlet.paired.v1",
            "seed": seed, "rounds": rounds, "cases": cases,
            "mean_squared_error": {
                "evidence_pool": pooled_error / rounds,
                "latest_claim": latest_error / rounds},
            "external_agents_executed": [],
            "scope": "synthetic evidence comparison, not AGI or peer-system test"}


if __name__ == "__main__":
    result = score()
    print(json.dumps({"mean_squared_error": result["mean_squared_error"],
                      "rounds": result["rounds"]}, indent=2))

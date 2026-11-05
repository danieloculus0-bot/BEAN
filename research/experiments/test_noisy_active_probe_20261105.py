"""Noisy target-label acquisition control for BEAN PR #291 (synthetic only).

Pre-registered policies: blind source, one noisy probe, majority of 5 probes.
All policies see identical target probes; only their inference differs.
"""
import hashlib
import json
import random
import unittest


def experiment(seed, shift, probe_noise=0.25, holdout_noise=0.10, n=256):
    rng = random.Random(seed)
    source = rng.randrange(2)
    target = source ^ int(shift)
    # Independent probes, never reused as evaluation rows.
    probes = [(x, (x ^ target) ^ int(rng.random() < probe_noise))
              for x in (rng.randrange(2) for _ in range(5))]
    estimates = [x ^ y for x, y in probes]
    rules = {"blind": source, "one_probe": estimates[0],
             "majority5": int(sum(estimates) >= 3)}
    holdout = [(x, (x ^ target) ^ int(rng.random() < holdout_noise))
               for x in (rng.randrange(2) for _ in range(n))]
    accuracy = {k: sum((x ^ rule) == y for x, y in holdout) / n
                for k, rule in rules.items()}
    receipt = hashlib.sha256(json.dumps({"seed": seed, "shift": shift,
        "probe_noise": probe_noise, "holdout_noise": holdout_noise,
        "probes": probes, "holdout": holdout, "accuracy": accuracy},
        sort_keys=True).encode()).hexdigest()
    return accuracy, receipt


class NoisyProbeControls(unittest.TestCase):
    def test_replay_and_distinct_seeds(self):
        self.assertEqual(experiment(41, True), experiment(41, True))
        self.assertNotEqual(experiment(41, True)[1], experiment(42, True)[1])

    def test_noisy_probes_can_mislead_one_shot(self):
        failures = sum(experiment(s, True, probe_noise=.4, holdout_noise=0)[0]["one_probe"] == 0
                       for s in range(200))
        self.assertGreater(failures, 40)

    def test_majority_improves_expected_shift_accuracy(self):
        trials = [experiment(s, True, probe_noise=.25)[0] for s in range(400)]
        one = sum(t["one_probe"] for t in trials) / len(trials)
        five = sum(t["majority5"] for t in trials) / len(trials)
        self.assertGreater(five, one + .05)

    def test_stationary_control_and_high_noise_failure(self):
        stable = [experiment(s, False, probe_noise=.25)[0] for s in range(200)]
        self.assertGreater(sum(t["blind"] for t in stable)/len(stable), .85)
        noisy = [experiment(s, True, probe_noise=.5)[0] for s in range(200)]
        self.assertLess(abs(sum(t["majority5"] for t in noisy)/len(noisy)-.5), .12)


if __name__ == "__main__":
    unittest.main()

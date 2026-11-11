"""Independent source-replay auditor for BEAN's SCAN reverse-order receipts.

This verifier does not import the candidate, its source selector or its
prediction functions. It downloads and checks the independently published,
pinned SCAN split and reconstructs all held-out answers, paired scores,
source memberships, failure cases and receipt digests.

python -m bean.tests.test_scan_reverse_order_audit reverse-scan-receipt.json
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
import sys
import unittest
from urllib.request import Request, urlopen

SCHEMA = "bean.scan_reverse_order.v1"
SEED = "bean-scan-reverse-order-independent-20261102"
ROOT = "https://raw.githubusercontent.com/brendenlake/SCAN/master/add_prim_split/"
PINNED = {
    "train": ("tasks_train_addprim_jump.txt",
              "87ed95fdc6851931ac9bf2f8932f245e75352ea5"),
    "test": ("tasks_test_addprim_jump.txt",
             "242eb2c7effc8673010868b854bc8e0a4c42c42c"),
}
POLICIES = ("learned", "phrase", "blind")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode()).hexdigest()


def source_ref(command):
    return "scan:train:" + sha256(command.encode()).hexdigest()[:24]


def source_data():
    sources, hashes = {}, {}
    for key, (filename, blob) in PINNED.items():
        with urlopen(Request(ROOT + filename, headers={
                "User-Agent": "BEAN-independent-SCAN-audit/1.0"}), timeout=30) as r:
            raw = r.read(8_000_001)
        if len(raw) > 8_000_000 or sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != blob:
            raise ValueError("Source blob mismatch: " + key)
        parsed = {}
        for line in raw.decode("utf-8").splitlines():
            match = re.fullmatch(r"IN: (.+?) OUT: ([A-Z_ ]+)", line.strip())
            if not match:
                raise ValueError("Malformed SCAN line")
            command, output = match.groups()
            if command in parsed and parsed[command] != output:
                raise ValueError("Conflicting source labels")
            parsed[command] = output
        sources[key] = parsed
        hashes[key] = {
            "git_blob_sha1": blob, "download_sha256": sha256(raw).hexdigest(),
            "unique_commands": len(parsed),
        }
    if set(sources["train"]) & set(sources["test"]):
        raise ValueError("Train/test overlap")
    return sources, hashes


def eligible(train, test):
    universe = dict(train)
    universe.update(test)
    selected = []
    for command, output in test.items():
        if command.count(" after ") != 1:
            continue
        left, right = command.split(" after ")
        if left not in universe or right not in universe:
            continue
        a, b = universe[left], universe[right]
        if a != b and output == b + " " + a and output != a + " " + b:
            selected.append(command)
    return sorted(selected, key=lambda c: (
        sha256((SEED + ":" + c).encode()).hexdigest(), c))


def paired_exact_test(deltas):
    """Two-sided exact paired sign test, conditional on discordant cases.

    Ties and joint failures carry no directional evidence. No asymptotic
    approximation or independent-case fiction for paired policy outputs.
    """
    if not isinstance(deltas, list) or any(type(x) is not int or x not in (-1, 0, 1)
                                            for x in deltas):
        raise ValueError("Expected paired integer differences in {-1,0,1}")
    from math import comb
    wins = deltas.count(1)
    losses = deltas.count(-1)
    n = wins + losses
    p = min(1.0, 2.0 * sum(comb(n, k) for k in range(min(wins, losses) + 1)) / (2 ** n)) if n else 1.0
    return {"wins": wins, "losses": losses, "ties": deltas.count(0),
            "discordant": n, "exact_two_sided_p": p,
            "candidate_superiority_at_0_05": wins > losses and p < 0.05}



def paired_family_sensitivity(commands, deltas):
    """Exploratory sign test at unordered operand-pair granularity.

    Swapped operand orders share the same underlying actions. They must not
    automatically count as independent evidence. A family contributes only
    the sign of its summed paired difference. This is a sensitivity check,
    not a proof that different families are statistically independent.
    """
    if len(commands) != len(deltas):
        raise ValueError("Commands and paired deltas must align")
    if any(type(x) is not int or x not in (-1, 0, 1) for x in deltas):
        raise ValueError("Invalid paired delta")
    groups = {}
    for command, delta in zip(commands, deltas):
        if not isinstance(command, str) or command.count(" after ") != 1:
            raise ValueError("Expected one after operator")
        left, right = command.split(" after ")
        if not left or not right:
            raise ValueError("Empty operand")
        key = tuple(sorted((left, right)))
        groups[key] = groups.get(key, 0) + delta
    family_deltas = [int(value > 0) - int(value < 0)
                     for _, value in sorted(groups.items())]
    return {"family_count": len(groups),
            "case_count": len(commands),
            "method": "unordered_operand_pair_sensitivity_not_independence_proof",
            **paired_exact_test(family_deltas)}



def paired_operand_overlap_sensitivity(commands, deltas):
    """Conservative sensitivity analysis for shared atomic actions.

    Operand-pair families are NOT independent if they share an action.
    Form connected components of the undirected action graph; aggregate
    paired deltas within each component and test component signs. This is
    intentionally pessimistic: a connected graph may collapse to one unit.
    It is not a causal independence guarantee or a primary significance test.
    """
    if len(commands) != len(deltas):
        raise ValueError("Commands and paired deltas must align")
    if any(type(x) is not int or x not in (-1, 0, 1) for x in deltas):
        raise ValueError("Invalid paired delta")
    parent = {}

    def root(item):
        parent.setdefault(item, item)
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for command in commands:
        if not isinstance(command, str) or command.count(" after ") != 1:
            raise ValueError("Expected one after operator")
        left, right = command.split(" after ")
        if not left or not right:
            raise ValueError("Empty operand")
        a, b = root(left), root(right)
        if a != b:
            parent[max(a, b)] = min(a, b)
    sums = {}
    for command, delta in zip(commands, deltas):
        left = command.split(" after ")[0]
        component = root(left)
        sums[component] = sums.get(component, 0) + delta
    signs = [int(v > 0) - int(v < 0) for _, v in sorted(sums.items())]
    return {"component_count": len(signs), "case_count": len(commands),
            "method": "shared_operand_connected_components_conservative_sensitivity",
            **paired_exact_test(signs)}


def audit(report, sources, hashes):
    if report.get("schema") != SCHEMA or report.get("selection_seed") != SEED:
        raise ValueError("Schema or selection seed changed")
    if report.get("source_hashes") != hashes:
        raise ValueError("Source hashes changed")
    train, test = sources["train"], sources["test"]
    training = report["training_rows"]
    if (len(training) != 1024 or report.get("training_budget") != 1024
            or len({row[0] for row in training}) != 1024):
        raise ValueError("Source budget or uniqueness mismatch")
    if any(not isinstance(row, list) or len(row) != 2
           or train.get(row[0]) != row[1] for row in training):
        raise ValueError("Source-only training mismatch")
    if report["training_rows_sha256"] != digest(training):
        raise ValueError("Training archive SHA mismatch")
    candidates = eligible(train, test)
    if report.get("eligible_pool") != len(candidates):
        raise ValueError("Eligible pool mismatch")
    commands = candidates[:96]
    rows = report["case_receipts"]
    if len(commands) != 96 or len(rows) != 96 or report.get("holdout_budget") != 96:
        raise ValueError("Incomplete held-out cohort")
    if report.get("case_receipts_sha256") != digest(rows):
        raise ValueError("Case archive SHA mismatch")
    if not report.get("snapshot_restart_verified") or not report.get(
            "native_sqlite_restart_verified"):
        raise ValueError("Missing restart checks")
    states = report["state_sha256"]
    if set(states) != set(POLICIES) or any(
            not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in states.values()):
        raise ValueError("Invalid model hashes")
    valid_refs = {source_ref(row[0]) for row in training}
    scores = {p: 0 for p in POLICIES}
    coverage = {p: 0 for p in POLICIES}
    failures = []
    paired_blind, paired_phrase = [], []
    for command, row in zip(commands, rows):
        left, right = command.split(" after ")
        if (row.get("command") != command or row.get("left") != left
                or row.get("right") != right
                or row.get("scorer_only_output") != test[command]
                or row.get("state_sha256") != states):
            raise ValueError("Held-out truth, order or state mismatch")
        if (set(row["predictions"]) != set(POLICIES)
                or set(row["correct"]) != set(POLICIES)
                or set(row["evidence_refs"]) != set(POLICIES)
                or set(row["reasons"]) != set(POLICIES)
                or set(row["composed"]) != set(POLICIES)):
            raise ValueError("Missing paired policy")
        for p in POLICIES:
            if not set(row["evidence_refs"][p]).issubset(valid_refs):
                raise ValueError("Fabricated evidence reference")
            if type(row["composed"][p]) is not bool:
                raise ValueError("Malformed composed flag")
            prediction = row["predictions"][p]
            if prediction is not None and not isinstance(prediction, str):
                raise ValueError("Malformed prediction")
            correct = prediction == test[command]
            if row["correct"][p] is not correct:
                raise ValueError("Incorrect score flag")
            scores[p] += int(correct)
            coverage[p] += int(prediction is not None)
        paired_blind.append(int(row["correct"]["learned"]) -
                            int(row["correct"]["blind"]))
        paired_phrase.append(int(row["correct"]["learned"]) -
                             int(row["correct"]["phrase"]))
        if not row["correct"]["learned"]:
            failures.append({"command": command, "reason": row["reasons"]["learned"]})
        if row["case_sha256"] != digest({
                key: value for key, value in row.items() if key != "case_sha256"}):
            raise ValueError("Case receipt SHA mismatch")
    if (scores != report["scores_exact_match"]
            or coverage != report["coverage"]
            or paired_blind != report["paired_learned_minus_blind"]
            or paired_phrase != report["paired_learned_minus_phrase"]
            or failures != report["candidate_failures"]):
        raise ValueError("Aggregate scores or negative evidence mismatch")
    return {"operand_overlap_vs_blind": paired_operand_overlap_sensitivity(commands, paired_blind),
            "operand_overlap_vs_phrase": paired_operand_overlap_sensitivity(commands, paired_phrase),
            "family_sensitivity_vs_blind": paired_family_sensitivity(commands, paired_blind),
            "family_sensitivity_vs_phrase": paired_family_sensitivity(commands, paired_phrase),
            "paired_learned_vs_blind": paired_exact_test(paired_blind),
            "paired_learned_vs_phrase": paired_exact_test(paired_phrase),
            "cases_verified": len(rows), "eligible_pool": len(candidates),
            "scores": scores, "coverage": coverage,
            "candidate_failures_preserved": len(failures),
            "case_receipts_sha256": report["case_receipts_sha256"]}


class IndependentAuditControls(unittest.TestCase):
    def test_reverse_order_scorer_excludes_same_action(self):
        train = {"walk": "I_WALK", "run": "I_RUN"}
        test = {"walk after run": "I_RUN I_WALK",
                "run after walk": "I_WALK I_RUN",
                "walk after walk": "I_WALK I_WALK"}
        self.assertEqual(set(eligible(train, test)),
                         {"walk after run", "run after walk"})

    def test_exact_paired_uncertainty_and_negative_controls(self):
        self.assertEqual(paired_exact_test([0] * 96)["exact_two_sided_p"], 1.0)
        self.assertFalse(paired_exact_test([1] * 4 + [-1] * 4)["candidate_superiority_at_0_05"])
        strong = paired_exact_test([1] * 8 + [0] * 88)
        self.assertEqual(strong["wins"], 8)
        self.assertEqual(strong["discordant"], 8)
        self.assertAlmostEqual(strong["exact_two_sided_p"], 2 / 256)
        self.assertTrue(strong["candidate_superiority_at_0_05"])
        self.assertFalse(paired_exact_test([-1] * 8)["candidate_superiority_at_0_05"])
        with self.assertRaises(ValueError):
            paired_exact_test([True])

    def test_family_sensitivity_prevents_swapped_order_pseudoreplication(self):
        commands = ["walk after run", "run after walk"] * 8
        deltas = [1] * 16
        naive = paired_exact_test(deltas)
        grouped = paired_family_sensitivity(commands, deltas)
        self.assertTrue(naive["candidate_superiority_at_0_05"])
        self.assertEqual(grouped["family_count"], 1)
        self.assertEqual(grouped["wins"], 1)
        self.assertFalse(grouped["candidate_superiority_at_0_05"])
        self.assertEqual(grouped["exact_two_sided_p"], 1.0)
        cancellation = paired_family_sensitivity(commands, [1, -1] * 8)
        self.assertEqual(cancellation["ties"], 1)
        self.assertFalse(cancellation["candidate_superiority_at_0_05"])
        with self.assertRaises(ValueError):
            paired_family_sensitivity(commands, [1])
        with self.assertRaises(ValueError):
            paired_family_sensitivity(["malformed"], [1])

    def test_shared_operand_components_block_false_independence(self):
        # Four different unordered pairs but a single shared atomic action.
        commands = ["walk after run", "walk after jump",
                    "walk after look", "walk after turn"]
        deltas = [1] * 4
        self.assertEqual(paired_family_sensitivity(commands, deltas)["family_count"], 4)
        grouped = paired_operand_overlap_sensitivity(commands, deltas)
        self.assertEqual(grouped["component_count"], 1)
        self.assertEqual(grouped["exact_two_sided_p"], 1.0)
        self.assertFalse(grouped["candidate_superiority_at_0_05"])
        # Disjoint pairs retain independent graph components for sensitivity.
        disjoint = ["walk after run", "jump after look", "turn after crawl"]
        result = paired_operand_overlap_sensitivity(disjoint, [1, -1, 0])
        self.assertEqual(result["component_count"], 3)
        self.assertEqual((result["wins"], result["losses"], result["ties"]), (1, 1, 1))
        self.assertEqual(paired_operand_overlap_sensitivity([], [])["component_count"], 0)
        with self.assertRaises(ValueError):
            paired_operand_overlap_sensitivity(commands, [1])
        with self.assertRaises(ValueError):
            paired_operand_overlap_sensitivity(["bad"], [1])

    def test_digest_detects_mutation(self):
        row = {"command": "walk after run", "correct": {"learned": True}}
        before = digest(row)
        row["correct"]["learned"] = False
        self.assertNotEqual(before, digest(row))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m bean.tests.test_scan_reverse_order_audit REPORT.json")
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    data, hashes = source_data()
    print(json.dumps(audit(report, data, hashes), sort_keys=True))

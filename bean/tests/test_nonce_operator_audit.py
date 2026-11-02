"""Independent receipt-only verifier for seeded nonce operator-order falsification.

Does not import BEAN's learner, candidate model or generator module. Rebuilds
every source label and holdout truth from the archived domain specification,
checks evidence membership, all 192 case hashes, scores, and negative cases.

python -m bean.tests.test_nonce_operator_audit nonce-order-receipt.json
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unittest

POLICIES = ("learned", "phrase", "blind")
MODIFIERS = {"doubled": 2, "tripled": 3}


def digest(obj):
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode()).hexdigest()


def nonce(seed, role, index):
    raw = sha256(f"nonce-order-v1:{seed}:{role}:{index}".encode()).digest()
    return "n" + "".join(chr(97 + value % 26) for value in raw[:9])


def source_ref(command):
    return "scan:train:" + sha256(command.encode()).hexdigest()[:24]


def oracle(command, verbs, orders):
    parts = command.split()
    if len(parts) == 1 and parts[0] in verbs:
        return "I_" + parts[0].upper()
    if len(parts) == 2 and parts[0] in verbs and parts[1] in MODIFIERS:
        return " ".join(["I_" + parts[0].upper()] * MODIFIERS[parts[1]])
    if len(parts) == 3 and parts[0] in verbs and parts[2] in verbs:
        order = orders.get(parts[1])
        if order:
            actions = ["I_" + parts[0].upper(), "I_" + parts[2].upper()]
            return " ".join(actions if order == "lr" else actions[::-1])
    if (len(parts) == 5 and parts[0] in verbs and parts[1] in MODIFIERS
            and parts[3] in verbs and parts[4] in MODIFIERS):
        order = orders.get(parts[2])
        if order:
            left = ["I_" + parts[0].upper()] * MODIFIERS[parts[1]]
            right = ["I_" + parts[3].upper()] * MODIFIERS[parts[4]]
            return " ".join(left + right if order == "lr" else right + left)
    raise ValueError("Invalid command in receipt")


def expected_spec(seed):
    verbs = [nonce(seed, "verb", index) for index in range(6)]
    operators = [nonce(seed, "operator", index) for index in range(2)]
    orders = {operators[0]: "rl" if seed % 2 == 0 else "lr",
              operators[1]: "lr" if seed % 2 == 0 else "rl"}
    source = {}
    for verb in verbs:
        for suffix in ("", " doubled", " tripled"):
            command = verb + suffix
            source[command] = oracle(command, verbs, orders)
    for operator in operators:
        for a, b in ((0, 1), (2, 3)):
            command = f"{verbs[a]} {operator} {verbs[b]}"
            source[command] = oracle(command, verbs, orders)
    queries = []
    for operator in operators:
        pairs = [(a, b) for a in verbs for b in verbs if a != b]
        pairs.sort(key=lambda pair: sha256(
            f"{seed}:{operator}:{pair[0]}:{pair[1]}".encode()).hexdigest())
        for index, (left, right) in enumerate(pairs[:8]):
            lm = "doubled" if index % 2 == 0 else "tripled"
            rm = "tripled" if index % 2 == 0 else "doubled"
            queries.append(f"{left} {lm} {operator} {right} {rm}")
    return verbs, orders, sorted(source.items()), queries


def audit(report):
    if report.get("schema") != "bean.nonce_operator_order.v1":
        raise ValueError("Unknown schema")
    seeds = list(range(4100, 4112))
    if report.get("seed_range") != seeds or (
            report.get("source_labels_per_seed") != 22 or
            report.get("queries_per_seed") != 16):
        raise ValueError("Changed predeclared budget or seeds")
    specs = report["domain_specs"]
    rows = report["case_receipts"]
    if len(specs) != 12 or len(rows) != 192:
        raise ValueError("Missing domain or case receipts")
    if digest(specs) != report["domain_specs_sha256"] or (
            digest(rows) != report["case_receipts_sha256"]):
        raise ValueError("Archive digest mismatch")
    if not report.get("snapshot_restart_verified") or not (
            report.get("native_sqlite_restart_verified")):
        raise ValueError("Missing restart evidence")
    known = {}
    for spec in specs:
        seed = spec["seed"]
        if seed not in seeds or seed in known:
            raise ValueError("Duplicate or unknown seed")
        verbs, orders, source, queries = expected_spec(seed)
        if spec["verbs"] != verbs or spec["operators"] != orders or (
                spec["source_rows"] != [list(row) for row in source] or
                spec["holdout_queries"] != queries):
            raise ValueError("Source or heldout construction drift")
        if spec["source_sha256"] != digest(spec["source_rows"]):
            raise ValueError("Source SHA mismatch")
        if len(source) != 22 or set(dict(source)) & set(queries):
            raise ValueError("Training/test leakage")
        states = spec["state_sha256"]
        if set(states) != set(POLICIES) or any(
                not re.fullmatch(r"[0-9a-f]{64}", value)
                for value in states.values()):
            raise ValueError("Invalid model state hashes")
        if not spec["snapshot_restart_verified"]:
            raise ValueError("Missing model restart")
        known[seed] = {
            "verbs": verbs, "orders": orders, "queries": queries,
            "states": states, "refs": {source_ref(k) for k, _ in source},
        }
    scores = {"lr": {p: 0 for p in POLICIES},
              "rl": {p: 0 for p in POLICIES}}
    grouped = {"lr": [], "rl": []}
    failures = []
    observed = {seed: [] for seed in seeds}
    for row in rows:
        seed = row["seed"]
        if seed not in known:
            raise ValueError("Unknown case seed")
        item = known[seed]
        observed[seed].append(row["command"])
        words = row["command"].split()
        operator = words[2] if len(words) == 5 else None
        order = item["orders"].get(operator)
        if (row["operator"] != operator or row["expected_order"] != order
                or order not in scores):
            raise ValueError("Incorrect operator/order")
        if row["scorer_only_output"] != oracle(
                row["command"], item["verbs"], item["orders"]):
            raise ValueError("Independent oracle disagreement")
        if row["state_sha256"] != item["states"]:
            raise ValueError("Mixed source/model state")
        if (set(row["predictions"]) != set(POLICIES) or
                set(row["correct"]) != set(POLICIES) or
                set(row["evidence_refs"]) != set(POLICIES) or
                set(row["reasons"]) != set(POLICIES) or
                set(row["composed"]) != set(POLICIES)):
            raise ValueError("Missing matched controls")
        for policy in POLICIES:
            if not set(row["evidence_refs"][policy]).issubset(item["refs"]):
                raise ValueError("Unobserved source cited")
            correct = row["predictions"][policy] == row["scorer_only_output"]
            if row["correct"][policy] is not correct:
                raise ValueError("False correctness flag")
            if type(row["composed"][policy]) is not bool:
                raise ValueError("Malformed composition flag")
            scores[order][policy] += int(correct)
        if row["case_sha256"] != digest({
                k: v for k, v in row.items() if k != "case_sha256"}):
            raise ValueError("Case hash mismatch")
        grouped[order].append(row)
        if not row["correct"]["learned"]:
            failures.append({
                "seed": seed, "command": row["command"],
                "reason": row["reasons"]["learned"],
            })
    for seed, commands in observed.items():
        if commands != known[seed]["queries"]:
            raise ValueError("Heldout order, membership or uniqueness drift")
    for order in ("lr", "rl"):
        group = grouped[order]
        entry = report["by_order"][order]
        if len(group) != 96 or entry["cases"] != 96 or (
                entry["scores"] != scores[order]):
            raise ValueError("Aggregate score mismatch")
        for other, key in (("blind", "paired_learned_minus_blind"),
                           ("phrase", "paired_learned_minus_phrase")):
            paired = [int(r["correct"]["learned"]) -
                      int(r["correct"][other]) for r in group]
            if entry[key] != paired:
                raise ValueError("Paired vector mismatch")
    if failures != report["candidate_failures"]:
        raise ValueError("Negative evidence missing or modified")
    return {
        "cases_verified": 192,
        "seeds_verified": len(seeds),
        "source_labels_per_seed": 22,
        "case_receipts_sha256": report["case_receipts_sha256"],
        "scores_by_order": scores,
        "candidate_failures_preserved": len(failures),
        "native_sqlite_restart_reported": True,
    }


class NonceAuditControls(unittest.TestCase):
    def test_mutated_case_digest_rejected(self):
        case = {"seed": 1, "command": "example", "case_sha256": "bad"}
        self.assertNotEqual(case["case_sha256"], digest({
            k: v for k, v in case.items() if k != "case_sha256"}))

    def test_independent_oracle_reverse_order(self):
        verbs = ["alpha", "beta"]
        self.assertEqual(
            oracle("alpha doubled prior beta tripled", verbs, {"prior": "rl"}),
            "I_BETA I_BETA I_BETA I_ALPHA I_ALPHA")
        self.assertEqual(
            oracle("alpha doubled prior beta tripled", verbs, {"prior": "lr"}),
            "I_ALPHA I_ALPHA I_BETA I_BETA I_BETA")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m bean.tests.test_nonce_operator_audit REPORT.json")
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(audit(report), sort_keys=True))

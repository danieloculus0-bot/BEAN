"""BEAN Information Balloon: adaptive *lossless* storage research.

Hypothesis: propose reversible content-aware dictionaries, mutate recipes,
and find the least costly method that meets an explicit retention budget and
query-recall objective. Not connected to production BEAN learning or memory.

Every accepted package must pass exact byte recovery. A checksum detects
accidental corruption; an optional external HMAC key authenticates packages.
A log of all trials, including regressions, is returned to the caller.
"""
from __future__ import annotations

import base64
import bz2
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import lzma
import math
import random
import statistics
import struct
import time
import zlib

VERSION = "bean.balloon.lossless.v1"
MAGIC = b"BEANB1\x00"
MAX_RAW = 2_000_000
MAX_HEADER = 32_768
MAX_PACKAGE = 2_500_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Recipe:
    codec: str = "zlib"
    level: int = 6
    gram: int = 0
    slots: int = 0

    def validate(self):
        if self.codec not in ("raw", "zlib", "bz2", "lzma"):
            raise ValueError("unsupported codec")
        limits = {"raw": (0,), "zlib": (1, 3, 6, 9),
                  "bz2": (1, 9), "lzma": (0, 3, 6)}
        if self.level not in limits[self.codec]:
            raise ValueError("unsupported compression level")
        if self.gram not in (0, 4, 6, 8, 12):
            raise ValueError("invalid dictionary gram")
        if self.slots not in (0, 8, 16, 32):
            raise ValueError("invalid dictionary size")
        if (self.gram == 0) != (self.slots == 0):
            raise ValueError("dictionary gram and slots must be paired")
        if self.gram and self.codec != "zlib":
            raise ValueError("tokenized recipes use a zlib backend")
        return self


def discover_tokens(training, recipe):
    """BEAN's own byte-level reversible token hypothesis, trained on training only.

    Candidate n-grams compete on approximate net bit savings; actual
    compression ratio and integrity are determined by measurements, not this
    prediction. No source bytes are discarded.
    """
    if not recipe.gram:
        return []
    counts = Counter(training[i:i + recipe.gram]
                     for i in range(len(training) - recipe.gram + 1))
    ranking = []
    for token, count in counts.items():
        if count >= 2:
            gain = count * (len(token) - 2) - (len(token) + 2)
            if gain > 0:
                ranking.append((gain, token))
    ranking.sort(key=lambda pair: (-pair[0], pair[1]))
    return [token for _, token in ranking[:recipe.slots]]


def token_encode(data, tokens):
    if not tokens:
        return data
    order = sorted(enumerate(tokens, 1), key=lambda t: (-len(t[1]), t[0]))
    output = bytearray()
    i = 0
    while i < len(data):
        chosen = next(((identifier, token) for identifier, token in order
                       if data.startswith(token, i)), None)
        if chosen:
            identifier, token = chosen
            output.extend((0, identifier))
            i += len(token)
        elif data[i] == 0:
            output.extend((0, 0))
            i += 1
        else:
            output.append(data[i])
            i += 1
    return bytes(output)


def token_decode(data, tokens, maximum):
    if not tokens:
        if len(data) > maximum:
            raise ValueError("decoded data exceeds declared size")
        return data
    output = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0:
            if i + 1 == len(data):
                raise ValueError("dangling dictionary escape")
            identifier = data[i + 1]
            if identifier > len(tokens):
                raise ValueError("unknown dictionary symbol")
            chunk = tokens[identifier - 1] if identifier else b"\x00"
            i += 2
        else:
            chunk = data[i:i + 1]
            i += 1
        if len(output) + len(chunk) > maximum:
            raise ValueError("dictionary expansion exceeds declared size")
        output.extend(chunk)
    return bytes(output)


def encode_backend(data, recipe):
    if recipe.codec == "raw":
        return data
    if recipe.codec == "zlib":
        return zlib.compress(data, recipe.level)
    if recipe.codec == "bz2":
        return bz2.compress(data, compresslevel=recipe.level)
    return lzma.compress(data, preset=recipe.level)


def decode_backend(data, codec, limit):
    """Bound decoded memory; reject concatenated streams and trailing bytes."""
    if codec == "raw":
        output, eof, extra = data, True, b""
    elif codec == "zlib":
        d = zlib.decompressobj()
        output = d.decompress(data, limit + 1)
        eof, extra = d.eof, d.unused_data + d.unconsumed_tail
    elif codec == "bz2":
        d = bz2.BZ2Decompressor()
        output = d.decompress(data, max_length=limit + 1)
        eof, extra = d.eof, d.unused_data if d.eof else b""
    elif codec == "lzma":
        d = lzma.LZMADecompressor()
        output = d.decompress(data, max_length=limit + 1)
        eof, extra = d.eof, d.unused_data if d.eof else b""
    else:
        raise ValueError("unsupported archive codec")
    if len(output) > limit or not eof or extra:
        raise ValueError("truncated, oversized or concatenated archive")
    return output


def pack(source, recipe, *, training=b"", key=None):
    """Self-describing, versioned byte-exact archive. Original kept by caller."""
    recipe.validate()
    if not isinstance(source, bytes) or len(source) > MAX_RAW:
        raise ValueError("source must be bytes within experiment capacity")
    if not isinstance(training, bytes) or len(training) > MAX_RAW:
        raise ValueError("training corpus must be bytes")
    if key is not None and (not isinstance(key, bytes) or len(key) < 16):
        raise ValueError("HMAC key must be at least 16 bytes")
    tokens = discover_tokens(training, recipe)
    transformed = token_encode(source, tokens)
    body = encode_backend(transformed, recipe)
    header = canonical({"schema": VERSION, "recipe": asdict(recipe),
                        "source_sha256": digest(source), "source_bytes": len(source),
                        "transformed_bytes": len(transformed),
                        "payload_sha256": digest(body),
                        "tokens": [base64.b64encode(x).decode("ascii") for x in tokens],
                        "authenticated": key is not None})
    if len(header) > MAX_HEADER:
        raise ValueError("archive metadata exceeds limit")
    archive = MAGIC + struct.pack(">I", len(header)) + header + body
    if key is not None:
        archive += hmac.digest(key, archive, "sha256")
    if len(archive) > MAX_PACKAGE:
        raise ValueError("archive exceeds experiment capacity")
    return archive


def unpack(archive, *, key=None, expected_hash=None):
    """Exact decoding with bounded allocation and optional external authenticator.

    Without a trusted manifest digest or HMAC key SHA-256 detects accidents, but
    does NOT prove a malicious party could not replace the whole package.
    """
    if not isinstance(archive, bytes) or len(archive) > MAX_PACKAGE:
        raise ValueError("invalid archive size/type")
    if len(archive) < len(MAGIC) + 4 or not archive.startswith(MAGIC):
        raise ValueError("invalid archive magic")
    if expected_hash is not None and not hmac.compare_digest(
            digest(archive), expected_hash):
        raise ValueError("trusted package digest mismatch")
    offset = len(MAGIC)
    size = struct.unpack(">I", archive[offset:offset + 4])[0]
    if not 0 < size <= MAX_HEADER or len(archive) < offset + 4 + size:
        raise ValueError("invalid archive header size")
    header = json.loads(archive[offset + 4:offset + 4 + size])
    if header.get("schema") != VERSION:
        raise ValueError("unsupported archive version")
    if type(header.get("source_bytes")) is not int or not 0 <= header["source_bytes"] <= MAX_RAW:
        raise ValueError("untrusted source size")
    if type(header.get("transformed_bytes")) is not int or not 0 <= header["transformed_bytes"] <= MAX_RAW * 2:
        raise ValueError("untrusted transformed size")
    recipe = Recipe(**header["recipe"]).validate()
    if type(header.get("authenticated")) is not bool:
        raise ValueError("invalid archive authentication mode")
    end = len(archive) - (32 if header["authenticated"] else 0)
    if end < offset + 4 + size:
        raise ValueError("truncated authenticated archive")
    if header["authenticated"]:
        if not isinstance(key, bytes) or len(key) < 16:
            raise ValueError("authentication key required")
        if not hmac.compare_digest(
                hmac.digest(key, archive[:end], "sha256"), archive[end:]):
            raise ValueError("archive authentication failed")
    payload = archive[offset + 4 + size:end]
    if digest(payload) != header["payload_sha256"]:
        raise ValueError("compressed payload integrity failure")
    tokens = [base64.b64decode(x, validate=True) for x in header["tokens"]]
    if (len(tokens) > 32 or
        any(len(token) != recipe.gram for token in tokens) or
        len(tokens) > recipe.slots or len(set(tokens)) != len(tokens)):
        raise ValueError("invalid token dictionary")
    transformed = decode_backend(payload, recipe.codec, header["transformed_bytes"])
    if len(transformed) != header["transformed_bytes"]:
        raise ValueError("archive transform length mismatch")
    recovered = token_decode(transformed, tokens, header["source_bytes"])
    if len(recovered) != header["source_bytes"] or digest(recovered) != header["source_sha256"]:
        raise ValueError("end-to-end SHA-256 mismatch")
    return recovered


def contextual_recall(records, queries, budget):
    """Recoverable *references* in active context; full content stays in archive.

    Ground truth and result are determined by exact tags on held-out synthetic
    records, not by an LLM grading its own summary.
    """
    if budget < 100:
        raise ValueError("context budget too small")
    scores = []
    for query in queries:
        expected = {r["id"] for r in records if query in r["tags"]}
        candidates = [{"id": r["id"], "sha256": digest(canonical(r))}
                      for r in records if query in r["tags"]]
        view = {"query": query, "refs": [], "total_matches": len(candidates)}
        for ref in candidates:
            view["refs"].append(ref)
            if len(canonical(view)) > budget:
                view["refs"].pop()
                break
        actual = {x["id"] for x in view["refs"]}
        scores.append({"query": query, "recall": (
            len(actual & expected) / len(expected) if expected else 1.0),
            "present": len(actual), "expected": len(expected),
            "bytes": len(canonical(view))})
    return {"mean_recall": sum(x["recall"] for x in scores) / len(scores)
            if scores else 1.0, "queries": scores}


def validate_records(records):
    if not isinstance(records, list) or not 3 <= len(records) <= 256:
        raise ValueError("experiment needs 3..256 records")
    seen = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != {"id", "text", "tags"}:
            raise ValueError("record contract requires id/text/tags")
        if not isinstance(row["id"], str) or not 0 < len(row["id"]) <= 70:
            raise ValueError("invalid record id")
        if row["id"] in seen:
            raise ValueError("duplicate record id")
        seen.add(row["id"])
        if not isinstance(row["text"], str) or len(row["text"]) > 10000:
            raise ValueError("invalid text")
        if not isinstance(row["tags"], list) or not all(
                isinstance(x, str) and 0 < len(x) <= 70 for x in row["tags"]):
            raise ValueError("invalid tags")
    if len(canonical(records)) > MAX_RAW:
        raise ValueError("dataset too large")


def fit_prefix(records, recipe, training, budget, *, key=None):
    """Maximum accepted prefix by exhaustive check, never silent source deletion.

    The output is a working shelf and lists every excluded ID. Caller keeps
    the original archive; a shelf is never a replacement retention policy.
    """
    if budget < 100:
        raise ValueError("storage budget too small")
    best, packed = 0, None
    for count in range(1, len(records) + 1):
        candidate = pack(canonical(records[:count]), recipe, training=training, key=key)
        if len(candidate) <= budget and count > best:
            if unpack(candidate, key=key) != canonical(records[:count]):
                raise AssertionError("candidate lost source bytes")
            best, packed = count, candidate
    return {"retained": best, "excluded_ids": [r["id"] for r in records[best:]],
            "archive": packed, "all_retained": best == len(records)}


def weissman_style(ratio, baseline_ratio, elapsed_ms, baseline_ms):
    """Dimensionless Weissman-*style* diagnostic, NOT the original formula.

    Original log(T) depends on units and can fail for T<=1. Here all times
    are explicitly normalized by a fixed 1-ms reference before log1p.
    """
    if min(ratio, baseline_ratio, elapsed_ms, baseline_ms) <= 0:
        raise ValueError("invalid positive Weissman inputs")
    return (ratio / baseline_ratio) * (
        math.log1p(baseline_ms / 1.0) /
        math.log1p(elapsed_ms / 1.0))


def benchmark_once(source, recipe, training, *, repeat=3):
    """No timing claims except measured values from this local process."""
    times = []
    archive = None
    for _ in range(repeat):
        start = time.perf_counter_ns()
        archive = pack(source, recipe, training=training)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        if unpack(archive) != source:
            raise AssertionError("failed exact round trip")
        times.append(max(elapsed, 0.000001))
    return {"bytes": len(archive), "ms_median": statistics.median(times),
            "ratio": len(source) / len(archive), "sha256": digest(archive),
            "exact": True}


def propose(best, visited, rng):
    """Test-time recipe inventor: mutate measured winner, then explore.

    This is a deterministic experimental search over reversible candidate
    encodings, not a pretrained neural coder or unbounded autonomous learner.
    """
    seeds = [Recipe("zlib", 6), Recipe("zlib", 1), Recipe("zlib", 9),
             Recipe("bz2", 1), Recipe("lzma", 0), Recipe("raw", 0),
             Recipe("zlib", 6, 6, 16), Recipe("zlib", 6, 4, 16)]
    for recipe in seeds:
        if recipe not in visited:
            return recipe, "baseline" if not recipe.gram else "self_dictionary"
    codecs = [Recipe("bz2", 9), Recipe("lzma", 3), Recipe("lzma", 6)]
    base = best if best and rng.random() < 0.8 else Recipe("zlib", 6, 6, 16)
    proposals = list(codecs)
    for _ in range(50):
        gram = rng.choice((0, 4, 6, 8, 12))
        slots = rng.choice((8, 16, 32)) if gram else 0
        level = rng.choice((1, 3, 6, 9))
        if base.codec == "zlib" and rng.random() < 0.5:
            gram = base.gram if rng.random() < 0.4 else gram
            slots = base.slots if gram == base.gram else slots
        proposals.append(Recipe("zlib", level, gram, slots))
    for recipe in proposals:
        if recipe not in visited:
            return recipe, "mutation"
    return None, "exhausted"


def run_experiment(records, *, archive_budget, context_budget,
                   queries, min_recall=1.0, iterations=14, seed=7):
    """Iterative selection with single final heldout test and immutable receipts.

    Train dictionary only on train partition. Tune proposals on a different
    partition. The final holdout is consulted once after recipe selection.
    Archived data are never deleted to make a benchmark pass.
    """
    validate_records(records)
    if not isinstance(queries, list) or not queries or not all(
            isinstance(q, str) and q for q in queries):
        raise ValueError("expected explicit relevance queries")
    if not 0 <= min_recall <= 1 or not 1 <= iterations <= 48:
        raise ValueError("invalid objective")
    if not isinstance(archive_budget, int) or not 100 <= archive_budget <= MAX_PACKAGE:
        raise ValueError("invalid archive budget")
    if not isinstance(context_budget, int) or not 100 <= context_budget <= 65536:
        raise ValueError("invalid context budget")
    rng = random.Random(seed)
    # Deterministic, disjoint partitions by record sequence. Holdout is not
    # referenced in the iterative feedback and cannot be used as a reward.
    n = len(records)
    first = max(1, n * 3 // 5)
    second = max(first + 1, n * 4 // 5)
    second = min(second, n - 1)
    training = canonical(records[:first])
    tuning = canonical(records[first:second])
    holdout = canonical(records[second:])
    baseline = benchmark_once(tuning, Recipe("zlib", 6), b"", repeat=3)
    # Rate target is derived from the declared whole-corpus storage budget.
    # Compression only needs to be strong enough to meet it; once feasible,
    # minimize measured work rather than chasing ever-higher ratios.
    target_ratio = len(canonical(records)) / archive_budget
    trials = []
    visited = set()
    leader, leader_metric, leader_rank = None, None, None
    for iteration in range(iterations):
        recipe, origin = propose(leader, visited, rng)
        if recipe is None:
            break
        visited.add(recipe)
        receipt = {"iteration": iteration, "recipe": asdict(recipe),
                   "proposed_by": origin, "training_sha256": digest(training),
                   "tuning_sha256": digest(tuning), "phase": "tuning"}
        try:
            metric = benchmark_once(tuning, recipe, training, repeat=3)
            metric["weissman_style"] = round(weissman_style(
                metric["ratio"], baseline["ratio"], metric["ms_median"],
                baseline["ms_median"]), 6)
            # A conservative proxy for full-archive feasibility; deployment
            # still verifies the actual full serialized source independently.
            feasible = metric["ratio"] >= target_ratio
            # Prefer feasible candidates and the least encode time. If none
            # fits, choose the best measured ratio, but report objective unmet.
            rank = ((1, -metric["ms_median"], metric["ratio"]) if feasible
                    else (0, metric["ratio"], -metric["ms_median"]))
            receipt.update({"result": "verified", "metric": metric,
                            "meets_estimated_rate_target": feasible,
                            "estimated_required_ratio": round(target_ratio, 6),
                            "selection_rank": list(rank)})
            if leader_rank is None or rank > leader_rank:
                leader, leader_metric, leader_rank = recipe, list(rank), rank
        except (ValueError, AssertionError, EOFError, OSError) as exc:
            receipt.update({"result": "failed", "error": type(exc).__name__})
        trials.append(receipt)
    if leader is None:
        return {"schema": VERSION, "accepted": False,
                "reason": "no_integrity_verified_candidate", "trials": trials}
    # One and only one evaluation of selected candidate on heldout bytes.
    final_holdout = benchmark_once(holdout, leader, training, repeat=3)
    final_holdout["weissman_style"] = round(weissman_style(
        final_holdout["ratio"], baseline["ratio"], final_holdout["ms_median"],
        baseline["ms_median"]), 6)
    shelf = fit_prefix(records, leader, training, archive_budget)
    active = records[:shelf["retained"]]
    recall = contextual_recall(active, queries, context_budget)
    objective_met = shelf["all_retained"] and recall["mean_recall"] >= min_recall
    return {"schema": VERSION, "accepted": bool(objective_met),
            "source_sha256": digest(canonical(records)),
            "source_records": len(records), "source_bytes": len(canonical(records)),
            "training_records": first, "tuning_records": second - first,
            "holdout_records": n - second,
            "budget_bytes": archive_budget,
            "context_budget_bytes": context_budget,
            "min_recall": min_recall, "candidate_count": len(trials),
            "selected_recipe": asdict(leader),
            "selection_priority": "meet_storage_goal_then_minimize_encoding_latency",
            "target_ratio": target_ratio,
            "selected_tuning_rank": leader_metric,
            "independent_holdout": final_holdout,
            "working_shelf_bytes": len(shelf["archive"]) if shelf["archive"] else None,
            "working_shelf_records": shelf["retained"],
            "omitted_ids": shelf["excluded_ids"], "relevance": recall,
            "reason": "meets_both_objectives" if objective_met else
                      "objective_unmet_retained_source_unchanged",
            "archive_sha256": digest(shelf["archive"]) if shelf["archive"] else None,
            "trials": trials}

"""Core BEAN memory capsule: score, compress, hash, and verify before retrieval.

Lossless storage is distinct from evidentiary truth: caller-supplied assessments
remain unverified until independently checked. Untrusted records are not promoted.
"""
from __future__ import annotations
import base64
import hashlib
import json
import math
import zlib

FORMAT = "bean.memory.capsule.v1"
LIMIT = 16 * 1024 * 1024

def canonical(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(raw) > LIMIT:
        raise ValueError("memory exceeds expansion limit")
    return raw

def score_evidence(*, accuracy, relevance, provenance, sample_count):
    metrics = (accuracy, relevance, provenance)
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in metrics):
        raise ValueError("assessment metrics must be finite in [0,1]")
    if type(sample_count) is not int or sample_count < 0:
        raise ValueError("invalid sample count")
    score = round(100 * (0.5 * accuracy + 0.3 * relevance + 0.2 * provenance), 2)
    return {"value": score, "samples": sample_count, "verified": False,
            "retrieval_eligible": score >= 60 and sample_count >= 30,
            "assessment_origin": "host_attested"}

def file_memory(value, *, accuracy, relevance, provenance, sample_count):
    # Scoring MUST succeed before serialization/compression and filing.
    assessment = score_evidence(accuracy=accuracy, relevance=relevance,
                                provenance=provenance, sample_count=sample_count)
    raw = canonical(value)
    digest = hashlib.sha256(raw).hexdigest()
    assessment_digest = hashlib.sha256(canonical({"memory_sha256": digest, "score": assessment})).hexdigest()
    compressed = zlib.compress(raw, 9)
    return {"format": FORMAT, "sha256": digest,
            "mnemonic": "-".join(digest[i:i+4] for i in (0,4,8,12)),
            "score": assessment, "assessment_sha256": assessment_digest, "raw_bytes": len(raw),
            "compressed_bytes": len(compressed),
            "payload": base64.b85encode(compressed).decode("ascii")}

def recover_memory(capsule, *, require_eligible=False):
    if not isinstance(capsule, dict) or capsule.get("format") != FORMAT:
        raise ValueError("unsupported capsule")
    score = capsule.get("score")
    if not isinstance(score, dict) or type(score.get("retrieval_eligible")) is not bool:
        raise ValueError("unscored memory")
    if (capsule.get("assessment_sha256") != hashlib.sha256(canonical({"memory_sha256": capsule.get("sha256"), "score": score})).hexdigest()):
        raise ValueError("assessment integrity mismatch")
    if require_eligible and not score["retrieval_eligible"]:
        raise ValueError("memory is ineligible for use")
    expected = capsule.get("sha256")
    if not isinstance(expected, str) or len(expected)!=64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("invalid hash")
    if capsule.get("mnemonic") != "-".join(expected[i:i+4] for i in (0,4,8,12)):
        raise ValueError("mnemonic mismatch")
    declared = capsule.get("raw_bytes")
    if type(declared) is not int or not 0 <= declared <= LIMIT:
        raise ValueError("invalid expansion size")
    try:
        zipped = base64.b85decode(capsule["payload"].encode("ascii"))
        if len(zipped) != capsule["compressed_bytes"]:
            raise ValueError("compressed size mismatch")
        decoder = zlib.decompressobj()
        raw = decoder.decompress(zipped, LIMIT + 1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("invalid compressed stream")
        if len(raw)!=declared or hashlib.sha256(raw).hexdigest()!=expected:
            raise ValueError("memory corruption")
        value = json.loads(raw)
        if canonical(value) != raw:
            raise ValueError("noncanonical memory")
        return value
    except (KeyError, TypeError, UnicodeError, ValueError, zlib.error) as exc:
        raise ValueError("corrupted capsule") from exc

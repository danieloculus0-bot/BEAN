"""Lossless compressed Q-value checkpoints with SHA-256 integrity and short mnemonic IDs."""
import base64
import hashlib
import json
import zlib

FORMAT = "bean.sponge.q.zlib85.v1"
MAX_EXPANDED = 16 * 1024 * 1024


def canonical(q):
    if not isinstance(q, dict):
        raise ValueError("Q table must be a dictionary")
    raw = json.dumps(q, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(raw) > MAX_EXPANDED:
        raise ValueError("Q table exceeds checkpoint limit")
    return raw


def pack(q):
    raw = canonical(q)
    digest = hashlib.sha256(raw).hexdigest()
    compressed = zlib.compress(raw, 9)
    return {
        "format": FORMAT,
        "sha256": digest,
        "mnemonic": "-".join(digest[i:i + 4] for i in (0, 4, 8, 12)),
        "uncompressed_bytes": len(raw),
        "compressed_bytes": len(compressed),
        "payload": base64.b85encode(compressed).decode("ascii"),
    }


def unpack(record):
    if not isinstance(record, dict) or record.get("format") != FORMAT:
        raise ValueError("unsupported checkpoint format")
    expected = record.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("missing SHA-256 digest")
    if record.get("mnemonic") != "-".join(expected[i:i + 4] for i in (0, 4, 8, 12)):
        raise ValueError("invalid mnemonic")
    declared = record.get("uncompressed_bytes")
    if type(declared) is not int or not 0 <= declared <= MAX_EXPANDED:
        raise ValueError("invalid declared size")
    try:
        compressed = base64.b85decode(record["payload"].encode("ascii"))
        if len(compressed) != record.get("compressed_bytes"):
            raise ValueError("compressed length mismatch")
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, MAX_EXPANDED + 1)
        if decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
            raise ValueError("invalid compressed stream")
        if len(raw) != declared or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("checkpoint hash or size mismatch")
        q = json.loads(raw.decode("utf-8"))
        if canonical(q) != raw:
            raise ValueError("noncanonical checkpoint")
        return q
    except (KeyError, TypeError, UnicodeError, zlib.error, ValueError) as exc:
        raise ValueError("invalid or corrupted Q checkpoint") from exc

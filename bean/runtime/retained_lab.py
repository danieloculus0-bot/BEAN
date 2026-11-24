"""Narrow native Core adapter to an isolated, SHA-checked retained skill worker.

No model-authored Python is imported into the production process. The host
controls socket location, supported contracts and worker sandbox. The worker
returns execution observations, not independent truth certification.
"""
import json
import math
import socket

MAX_BYTES = 16384


def validate_weighted_mean(args):
    if not isinstance(args, dict) or set(args) != {"values", "weights"}:
        raise ValueError("values and weights required")
    v, w = args["values"], args["weights"]
    if not isinstance(v, list) or not isinstance(w, list) or not 1 <= len(v) <= 128 or len(v) != len(w):
        raise ValueError("bounded equal nonempty arrays required")
    if any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e100 for x in v+w):
        raise ValueError("finite bounded numeric inputs required")
    if any(x < 0 for x in w) or sum(w) <= 0:
        raise ValueError("nonnegative weights with positive total required")
    return v,w


class RetainedLab:
    def __init__(self, socket_path):
        self.socket_path = socket_path

    def weighted_mean(self, args):
        validate_weighted_mean(args)
        request = json.dumps({"skill":"weighted_mean", **args}, allow_nan=False).encode() + b"\n"
        if len(request) > MAX_BYTES:
            raise ValueError("request too large")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(12)
            peer.connect(self.socket_path)
            peer.sendall(request)
            with peer.makefile("rb") as stream:
                reply = stream.readline(MAX_BYTES+1)
        if len(reply) > MAX_BYTES or not reply.endswith(b"\n"):
            raise ValueError("invalid worker response")
        result = json.loads(reply)
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise ValueError("retained skill worker failed")
        value, digest = result.get("value"), result.get("source_sha256")
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError("invalid retained result")
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("missing source digest")
        return {"status":"ok","value":value,"source_sha256":digest,
                "skill":"weighted_mean","execution":"isolated_retained_source",
                "independent_correctness_verified":False}


def register_retained_lab(orchestrator, inbox, socket_path):
    lab = RetainedLab(socket_path)
    orchestrator.register("retained_weighted_mean",
        "Execute a retained independently tested weighted mean skill: "
        "{values:[numbers],weights:[nonnegative numbers]}; returns value and source_sha256",
        lambda args, task_ref: lab.weighted_mean(args))
    inbox.register("retained_weighted_mean", lambda msg, session: lab.weighted_mean(msg.args))

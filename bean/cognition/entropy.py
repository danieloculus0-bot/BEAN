"""Deterministic entropy source for reproducible tie-breaking and noise."""

from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class EntropySourceType(str, Enum):
    DETERMINISTIC_PRNG = "deterministic_prng"
    SYSTEM_RANDOM = "system_random"
    QRNG = "qrng"


@dataclass
class EntropyReading:
    value: float
    source_type: EntropySourceType
    seed_ref: str
    usage_hint: str
    generated_at: str

    def to_dict(self) -> dict:
        return {"value": self.value, "source_type": self.source_type.value, "seed_ref": self.seed_ref, "usage_hint": self.usage_hint, "generated_at": self.generated_at}


class EntropySource:
    def __init__(self, source_type: EntropySourceType = EntropySourceType.DETERMINISTIC_PRNG):
        self.source_type = source_type
        self._rng = random.Random(0)
        self._seed_ref = "default:0"
        self._samples_drawn = 0
        self._qrng = None

    def seed_from_event_log(self, session_uuid: str):
        from ..memory.store import get_store
        rows = get_store().fetchall("SELECT event_uuid, event_type, summary, created_at FROM events WHERE session_uuid=? ORDER BY id", (session_uuid,))
        payload = "|".join(f"{r['event_uuid']}:{r['event_type']}:{r['summary']}:{r['created_at']}" for r in rows)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self._rng.seed(int(digest[:16], 16))
        self._seed_ref = f"event_log:{session_uuid}:{digest[:12]}"

    def sample(self, usage_hint: str = "unspecified") -> EntropyReading:
        if self.source_type == EntropySourceType.SYSTEM_RANDOM:
            value = int.from_bytes(os.urandom(8), "big") / float(2**64 - 1)
            seed_ref = "os.urandom"
        elif self.source_type == EntropySourceType.QRNG and self._qrng:
            value = float(self._qrng())
            seed_ref = "registered_qrng"
        else:
            value = self._rng.random()
            seed_ref = self._seed_ref
        self._samples_drawn += 1
        return EntropyReading(max(0.0, min(1.0, value)), self.source_type, seed_ref, usage_hint, datetime.now(timezone.utc).isoformat())

    def sample_gaussian(self, mean: float = 0.0, std: float = 0.05, usage_hint: str = "gaussian") -> EntropyReading:
        value = self._rng.gauss(mean, std)
        self._samples_drawn += 1
        return EntropyReading(value, self.source_type, f"gaussian:{self._seed_ref}", usage_hint, datetime.now(timezone.utc).isoformat())

    def register_qrng(self, reader_fn):
        self._qrng = reader_fn
        self.source_type = EntropySourceType.QRNG

    def usage_summary(self) -> dict:
        return {"source_type": self.source_type.value, "seed_ref": self._seed_ref, "samples_drawn": self._samples_drawn}

"""BEAN Watcher: RAM working state, recall scheduling and evidence-first ERP reports.

No live ERP credentials or connections are included. Report readers are authorized
adapters that return normalized, *explicitly complete* snapshots. State changes
can be written to BEAN's append-only SQLite event ledger through an event sink.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol

_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")


def _utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("report timestamp needs an explicit timezone")
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class WatchSpec:
    key: str
    fields: tuple[str, ...]
    recall_frequency: float = 60.0
    stale_after: float = 900.0

    def __post_init__(self):
        if not _KEY.fullmatch(self.key) or self.key in {".", ".."}:
            raise ValueError("Invalid report key")
        if not self.fields or len(set(self.fields)) != len(self.fields):
            raise ValueError("Each report must declare unique required fields")
        if any(not isinstance(f, str) or not f.strip() for f in self.fields):
            raise ValueError("Metric field names must be nonempty")
        if not 1 <= self.recall_frequency <= 86400 or not math.isfinite(self.recall_frequency):
            raise ValueError("recall_frequency must be 1..86400 seconds")
        if not self.stale_after >= self.recall_frequency or not math.isfinite(self.stale_after):
            raise ValueError("stale_after must be >= recall_frequency")


@dataclass(frozen=True)
class ReportEvidence:
    report_id: str
    observed_at: str
    complete: bool
    values: Mapping[str, object]
    evidence_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "ReportEvidence":
        if not isinstance(payload, Mapping):
            raise ValueError("report payload must be an object")
        if not isinstance(payload.get("report_id"), str) or not payload["report_id"].strip():
            raise ValueError("report_id required")
        if not isinstance(payload.get("observed_at"), str):
            raise ValueError("observed_at required")
        _utc(payload["observed_at"])
        if type(payload.get("complete")) is not bool:
            raise ValueError("complete must be explicitly true or false")
        values = payload.get("values")
        if not isinstance(values, dict):
            raise ValueError("values must be an object")
        refs = payload.get("evidence_ids", [])
        if not isinstance(refs, (tuple, list)) or not all(isinstance(x, str) and x.strip() for x in refs):
            raise ValueError("evidence_ids must be strings")
        return cls(payload["report_id"], payload["observed_at"],
                   payload["complete"], dict(values), tuple(refs))


class ReportReader(Protocol):
    def __call__(self, key: str) -> Optional[ReportEvidence]: ...


class DirectoryReportReader:
    """Read named normalized JSON exports; no file creation or ERP access."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def version(self, key: str) -> object:
        """Cheap stat signature, allows the next runtime tick to wake early."""
        if not _KEY.fullmatch(key) or key in {".", ".."}:
            raise ValueError("Invalid report key")
        path = self.directory / (key + ".json")
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            return None

    def __call__(self, key: str) -> Optional[ReportEvidence]:
        if not _KEY.fullmatch(key) or key in {".", ".."}:
            raise ValueError("Invalid report key")
        path = self.directory / (key + ".json")
        if not path.exists():
            return None
        if not path.is_file() or path.is_symlink():
            raise ValueError("Report input must be a regular file")
        return ReportEvidence.from_mapping(json.loads(path.read_text(encoding="utf-8")))


class BeanWatcher:
    """Memory-local state; durable transitions through an injectable event sink.

    Call poll_due from BEAN's runtime tick scheduler, or ingest when a report
    delivery event arrives. Both routes use the same evidence checks.
    """

    def __init__(
        self,
        specs: list[WatchSpec],
        reader: ReportReader,
        *,
        event_sink: Optional[Callable[[dict], None]] = None,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        if len({spec.key for spec in specs}) != len(specs):
            raise ValueError("Duplicate report keys")
        self.specs = {spec.key: spec for spec in specs}
        self.reader = reader
        self.event_sink = event_sink
        self.monotonic = monotonic
        self.utc_now = utc_now
        self._versions: dict[str, object] = {}
        self._state = {
            key: {
                "status": "n/a", "reason": "not_checked", "current": None,
                "last_verified": None, "checked_at": None, "next_recall": 0.0,
                "digest": None,
            } for key in self.specs
        }

    def _public(self, key: str) -> dict:
        state = self._state[key]
        spec = self.specs[key]
        current = state["current"]
        verified = state["last_verified"]
        if current is not None and _utc(current["observed_at"]) < self.utc_now().astimezone(timezone.utc) - timedelta(seconds=spec.stale_after):
            status, reason = "stale", "evidence_age_exceeded"
            current = None
        else:
            status, reason = state["status"], state["reason"]
        return {
            "key": key, "status": status, "reason": reason,
            "values": copy.deepcopy(current["values"]) if status == "verified" and current else {field: None for field in spec.fields},
            "last_verified": copy.deepcopy(verified),
            "checked_at": state["checked_at"],
            "recall_frequency": spec.recall_frequency,
            "next_recall_seconds": max(0.0, round(state["next_recall"] - self.monotonic(), 3)),
        }

    def snapshot(self, key: Optional[str] = None) -> dict:
        if key is not None:
            return self._public(key)
        return {name: self._public(name) for name in self.specs}

    def _apply(self, key: str, report: Optional[ReportEvidence], *, error: Optional[str] = None) -> dict:
        spec = self.specs[key]
        old = self._state[key]
        now = self.utc_now().astimezone(timezone.utc)
        current = None
        digest = None
        if error:
            status, reason = "n/a", "source_error"
        elif report is None:
            status, reason = "n/a", "report_missing"
        elif not isinstance(report, ReportEvidence):
            status, reason = "n/a", "invalid_report"
        elif not report.complete:
            status, reason = "n/a", "report_incomplete"
        elif not report.evidence_ids:
            status, reason = "n/a", "evidence_missing"
        elif _utc(report.observed_at) > now:
            status, reason = "n/a", "future_report"
        elif (now - _utc(report.observed_at)).total_seconds() > spec.stale_after:
            status, reason = "stale", "report_too_old"
        elif old["last_verified"] and _utc(report.observed_at) < _utc(old["last_verified"]["observed_at"]):
            status, reason = "n/a", "older_than_last_verified"
        elif any(field not in report.values or report.values[field] is None for field in spec.fields):
            status, reason = "n/a", "required_field_missing"
        elif any(type(report.values[f]) not in {int, float, str} or
                 (type(report.values[f]) is float and not math.isfinite(report.values[f]))
                 for f in spec.fields):
            status, reason = "n/a", "invalid_field_value"
        else:
            status, reason = "verified", "complete_report"
            current = {
                "report_id": report.report_id,
                "observed_at": report.observed_at,
                "values": {f: report.values[f] for f in spec.fields},
                "evidence_ids": list(report.evidence_ids),
            }
            digest = hashlib.sha256(json.dumps(current, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()
        new_last = current or old["last_verified"]
        checked = now.isoformat()
        next_recall = self.monotonic() + spec.recall_frequency
        changed = (old["status"], old["reason"], old["digest"]) != (status, reason, digest)
        if changed and self.event_sink is not None:
            # Write first; if durable logging fails, do not publish an unrecorded transition.
            self.event_sink({
                "type": "watcher_transition", "key": key, "status": status,
                "reason": reason, "digest": digest, "checked_at": checked,
                "current": copy.deepcopy(current), "last_verified": copy.deepcopy(new_last),
            })
        self._state[key] = {
            "status": status, "reason": reason, "current": current,
            "last_verified": new_last, "checked_at": checked,
            "next_recall": next_recall, "digest": digest,
        }
        return self._public(key)

    def ingest(self, key: str, report: Optional[ReportEvidence]) -> dict:
        if key not in self.specs:
            raise KeyError(key)
        return self._apply(key, report)

    def poll_due(self, *, force: bool = False) -> dict:
        output = {}
        for key in self.specs:
            version = None
            probe = getattr(self.reader, "version", None)
            if callable(probe):
                try:
                    version = probe(key)
                except OSError:
                    version = None
            changed = callable(probe) and key in self._versions and version != self._versions[key]
            if not force and not changed and self.monotonic() < self._state[key]["next_recall"]:
                continue
            try:
                report = self.reader(key)
                output[key] = self._apply(key, report)
            except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
                output[key] = self._apply(key, None, error="source_error")
            self._versions[key] = version
        return output

    def restore_events(self, events: list[dict]) -> None:
        """Recover only valid historical evidence; never treat it as a fresh reading.

        Malformed records are ignored instead of crashing startup or poisoning
        the recall watermark with a future or older fabricated timestamp.
        """
        for event in events:
            if not isinstance(event, dict) or event.get("type") != "watcher_transition":
                continue
            key = event.get("key")
            if not isinstance(key, str) or key not in self._state:
                continue
            record = event.get("last_verified")
            if not isinstance(record, dict):
                continue
            values = record.get("values")
            refs = record.get("evidence_ids")
            if not isinstance(record.get("report_id"), str) or not record["report_id"].strip():
                continue
            if not isinstance(values, dict) or not all(
                field in values for field in self.specs[key].fields
            ):
                continue
            if not isinstance(refs, (tuple, list)) or not refs or not all(
                isinstance(ref, str) and ref.strip() for ref in refs
            ):
                continue
            if any(
                type(values[field]) not in {int, float, str}
                or (type(values[field]) is float and not math.isfinite(values[field]))
                for field in self.specs[key].fields
            ):
                continue
            try:
                observed_at = _utc(record.get("observed_at"))
            except (TypeError, ValueError, AttributeError):
                continue
            if observed_at > self.utc_now().astimezone(timezone.utc):
                continue
            previous = self._state[key]["last_verified"]
            if previous is not None and observed_at < _utc(previous["observed_at"]):
                continue
            self._state[key]["last_verified"] = copy.deepcopy(record)
            self._state[key]["status"] = "n/a"
            self._state[key]["reason"] = "awaiting_recheck"
            self._state[key]["current"] = None
            self._state[key]["next_recall"] = 0.0


def load_watch_specs(path: str | Path) -> list[WatchSpec]:
    """Explicit configuration; no default connection to an ERP."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("reports"), list):
        raise ValueError("Expected reports array")
    specs = []
    for item in config["reports"]:
        if not isinstance(item, dict):
            raise ValueError("Each report must be an object")
        specs.append(WatchSpec(
            key=item["key"],
            fields=tuple(item["fields"]),
            recall_frequency=item.get("recall_frequency", 60),
            stale_after=item.get("stale_after", 900),
        ))
    return specs

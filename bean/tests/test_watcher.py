"""Synthetic evidence-contract tests for the native BEAN Watcher."""
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bean.runtime.watcher import (
    BeanWatcher, DirectoryReportReader, ReportEvidence, WatchSpec, load_watch_specs,
)
from bean.runtime.tick_handlers import build_default_handlers

START = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.seconds = 0.0

    def mono(self):
        return self.seconds

    def utc(self):
        return START + timedelta(seconds=self.seconds)

    def advance(self, seconds):
        self.seconds += seconds


def report(at=START, *, complete=True, values=None, refs=("file:sha256:abc",)):
    return ReportEvidence(
        report_id="synthetic-rma-001", observed_at=at.isoformat(),
        complete=complete, values={"rma_count": 0} if values is None else values,
        evidence_ids=refs,
    )


def make(reader=None, *, stale=300):
    clock = Clock()
    events = []
    items = []
    def source(key):
        return items[-1] if items else None
    watcher = BeanWatcher(
        [WatchSpec("rma", ("rma_count",), recall_frequency=60, stale_after=stale)],
        reader or source, event_sink=lambda e: events.append(e), monotonic=clock.mono,
        utc_now=clock.utc,
    )
    return watcher, clock, events, items


def test_missing_data_is_na_not_zero():
    watcher, clock, events, _ = make()
    state = watcher.poll_due()["rma"]
    assert state["status"] == "n/a"
    assert state["values"]["rma_count"] is None
    assert state["reason"] == "report_missing"
    assert events[-1]["current"] is None
    assert watcher.poll_due() == {}
    clock.advance(60)
    assert watcher.poll_due()["rma"]["status"] == "n/a"


def test_explicit_complete_zero_is_valid():
    watcher, _, _, items = make()
    items.append(report())
    state = watcher.poll_due()["rma"]
    assert state["status"] == "verified"
    assert state["values"]["rma_count"] == 0


def test_incomplete_report_never_claims_zero():
    watcher, _, _, items = make()
    items.append(report(complete=False))
    state = watcher.poll_due()["rma"]
    assert state["reason"] == "report_incomplete"
    assert state["values"]["rma_count"] is None


def test_missing_evidence_reference_is_na():
    watcher, _, _, items = make()
    items.append(report(refs=()))
    assert watcher.poll_due()["rma"]["reason"] == "evidence_missing"


def test_missing_required_field_never_implies_zero():
    watcher, _, _, items = make()
    items.append(report(values={}))
    state = watcher.poll_due()["rma"]
    assert state["status"] == "n/a"
    assert state["reason"] == "required_field_missing"


def test_new_report_replaces_active_values_without_erasing_history():
    watcher, clock, events, items = make()
    items.append(report())
    assert watcher.poll_due()["rma"]["values"]["rma_count"] == 0
    clock.advance(61)
    items.append(report(clock.utc(), values={"rma_count": 2}))
    new = watcher.poll_due()["rma"]
    assert new["values"]["rma_count"] == 2
    assert new["last_verified"]["values"]["rma_count"] == 2
    assert len(events) == 2
    assert events[0]["current"]["values"]["rma_count"] == 0


def test_missing_later_export_retains_last_verified_but_current_na():
    watcher, clock, events, items = make()
    items.append(report())
    watcher.poll_due()
    clock.advance(60)
    items.clear()
    missing = watcher.poll_due()["rma"]
    assert missing["values"]["rma_count"] is None
    assert missing["last_verified"]["values"]["rma_count"] == 0
    assert missing["status"] == "n/a"


def test_staleness_does_not_overwrite_history():
    watcher, clock, _, items = make(stale=120)
    items.append(report())
    watcher.poll_due()
    clock.advance(121)
    stale = watcher.snapshot("rma")
    assert stale["status"] == "stale"
    assert stale["values"]["rma_count"] is None
    assert stale["last_verified"]["values"]["rma_count"] == 0
    stale_after_poll = watcher.poll_due()["rma"]
    assert stale_after_poll["status"] == "stale"


def test_older_report_does_not_displace_newer_verified():
    watcher, clock, _, items = make(stale=300)
    clock.advance(90)
    items.append(report(clock.utc(), values={"rma_count": 5}))
    watcher.poll_due()
    clock.advance(61)
    items.append(report(START, values={"rma_count": 0}))
    state = watcher.poll_due()["rma"]
    assert state["status"] == "n/a"
    assert state["reason"] == "older_than_last_verified"
    assert state["last_verified"]["values"]["rma_count"] == 5


def test_fetch_error_stays_na():
    watcher, _, _, _ = make(reader=lambda key: (_ for _ in ()).throw(OSError("offline")))
    state = watcher.poll_due()["rma"]
    assert state["status"] == "n/a"
    assert state["reason"] == "source_error"


def test_repeat_unchanged_event_is_deduplicated():
    watcher, clock, events, items = make()
    items.append(report())
    watcher.poll_due()
    clock.advance(60)
    watcher.poll_due()
    assert len(events) == 1


def test_replay_keeps_history_but_needs_fresh_source():
    watcher, _, events, items = make()
    items.append(report())
    watcher.poll_due()
    restored, _, _, new_items = make()
    restored.restore_events(events)
    status = restored.snapshot("rma")
    assert status["values"]["rma_count"] is None
    assert status["last_verified"]["values"]["rma_count"] == 0
    assert status["reason"] == "awaiting_recheck"
    new_items.append(report())
    assert restored.poll_due()["rma"]["status"] == "verified"


def test_directory_reader_change_triggers_early_recall(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"reports": [
        {"key": "rma", "fields": ["rma_count"], "recall_frequency": 600, "stale_after": 1000}
    ]}))
    reader = DirectoryReportReader(tmp_path)
    clock = Clock()
    watcher = BeanWatcher(load_watch_specs(config), reader, monotonic=clock.mono, utc_now=clock.utc)
    assert watcher.poll_due()["rma"]["status"] == "n/a"
    p = tmp_path / "rma.json"
    p.write_text(json.dumps({
        "report_id": "synthetic-report", "observed_at": START.isoformat(),
        "complete": True, "values": {"rma_count": 0}, "evidence_ids": ["sha256:abcd"]
    }))
    clock.advance(1)
    assert watcher.poll_due()["rma"]["values"]["rma_count"] == 0
    clock.advance(1)
    assert watcher.poll_due() == {}
    p.unlink()
    clock.advance(1)
    assert watcher.poll_due()["rma"]["status"] == "n/a"


def test_runtime_handler_registration_calls_watcher():
    class FakeWatcher:
        def __init__(self):
            self.polls = 0
        def poll_due(self):
            self.polls += 1
    watcher = FakeWatcher()
    registry = build_default_handlers(watcher=watcher, reflection_interval=100)
    registration = next(h for h in registry._handlers if h.name == "bean_watcher")
    registration.fn(0, "synthetic", {})
    assert watcher.polls == 1


def test_invalid_configuration_rejected():
    with pytest.raises(ValueError):
        WatchSpec("../secret", ("rma_count",))
    with pytest.raises(ValueError):
        WatchSpec("rma", ("rma_count",), recall_frequency=0)
    with pytest.raises(ValueError):
        WatchSpec("rma", ("rma_count",), recall_frequency=60, stale_after=30)


def test_true_completeness_is_required_not_truthy_string():
    with pytest.raises(ValueError, match="complete"):
        ReportEvidence.from_mapping({
            "report_id": "x", "observed_at": START.isoformat(),
            "complete": "true", "values": {}, "evidence_ids": ["test"]
        })

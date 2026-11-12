"""Coverage-sensitive synthetic simulation metrics, independent of Core state."""
import pytest

from scripts.simulate_restored_core import coverage_metrics


def sample():
    return {
        "channel": {"correct": {"candidate": 48, "passive": 48,
                                 "shuffled": 0, "always_zero": 0},
                    "abstentions": {"candidate": 0, "passive": 0,
                                    "shuffled": 48}},
        "difference": {"correct": {"candidate": 48, "passive": 48,
                                    "shuffled": 0, "always_zero": 0},
                       "abstentions": {"candidate": 0, "passive": 0,
                                       "shuffled": 48}},
        "parity": {"correct": {"candidate": 0, "passive": 0,
                                "shuffled": 0, "always_zero": 0},
                   "abstentions": {"candidate": 48, "passive": 48,
                                   "shuffled": 48}},
    }


def test_historical_parity_abstention_not_wrong_attempt():
    result = coverage_metrics(sample())
    assert result["candidate"]["correct"] == 96
    assert result["candidate"]["attempted"] == 96
    assert result["candidate"]["coverage"] == pytest.approx(2 / 3)
    assert result["candidate"]["accuracy_when_attempted"] == 1
    assert result["candidate"]["all_case_accuracy"] == pytest.approx(2 / 3)
    assert result["candidate"]["families"]["parity"]["accuracy_when_attempted"] is None
    assert result["shuffled"]["accuracy_when_attempted"] is None
    assert result["always_zero"]["attempted"] == 144
    assert result["always_zero"]["accuracy_when_attempted"] == 0


def test_partial_coverage_and_misses():
    rows = sample()
    rows["channel"]["correct"]["candidate"] = 20
    rows["channel"]["abstentions"]["candidate"] = 8
    result = coverage_metrics(rows)
    assert result["candidate"]["attempted"] == 88
    assert result["candidate"]["correct"] == 68
    assert result["candidate"]["accuracy_when_attempted"] == pytest.approx(68 / 88)


@pytest.mark.parametrize("hits,abstained", [(49, 0), (1, 48), (-1, 0), (0, 49)])
def test_invalid_counts_rejected(hits, abstained):
    rows = sample()
    rows["parity"]["correct"]["candidate"] = hits
    rows["parity"]["abstentions"]["candidate"] = abstained
    with pytest.raises(ValueError):
        coverage_metrics(rows)


def test_missing_family_rejected():
    rows = sample()
    del rows["parity"]
    with pytest.raises(ValueError):
        coverage_metrics(rows)

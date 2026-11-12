"""Coverage-sensitive synthetic simulation metrics, independent of Core state."""
import pytest

from scripts.simulate_restored_core import coverage_metrics, nonlearning_controls


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


def test_nonlearning_controls_are_reproducible_and_nonabstaining():
    first = nonlearning_controls(26)
    assert first == nonlearning_controls(26)
    assert first["mode"] == "evaluator_only_post_learning"
    assert first["probes_or_reward_calls"] == 0
    assert first["all_case_attempts_per_control"] == 144
    totals = {name: 0 for name in (
        "always_negative", "always_positive", "uniform_random")}
    assert set(first["families"]) == {"channel", "difference", "parity"}
    for row in first["families"].values():
        assert row["attempted"] == 48
        counts = row["blind_truth_label_counts"]
        assert set(counts) == {"-1", "0", "1"}
        assert sum(counts.values()) == 48
        assert row["correct"]["always_negative"] == counts["-1"]
        assert row["correct"]["always_positive"] == counts["1"]
        for control, score in row["correct"].items():
            assert control in totals
            assert 0 <= score <= 48
            totals[control] += score
    assert totals == first["correct_totals"]


@pytest.mark.parametrize("invalid", [0, -1, True, 3.14, "26"])
def test_nonlearning_controls_require_positive_integer_generation(invalid):
    with pytest.raises(ValueError):
        nonlearning_controls(invalid)

from __future__ import annotations

import pandas as pd

from app.services.group_analysis.grouping import group_cycles_by_settings
from app.services.import_service.csv_import import ImportedCycle
from app.services.simulation.simulator import FasteningSettings


def _cycle(cycle_id: str, speed: float = 820.0) -> ImportedCycle:
    return ImportedCycle(
        cycle_id=cycle_id,
        settings=FasteningSettings(
            target_speed=speed,
            target_torque=1.2,
            clamp_rising_time=100.0,
            torque_hold_time=30.0,
        ),
        waveform=pd.DataFrame({"cycle_id": [cycle_id], "time_ms": [0.0], "torque": [0.0]}),
        metadata={},
        issues=[],
    )


def test_identical_settings_form_one_group():
    groups = group_cycles_by_settings([_cycle("A"), _cycle("B"), _cycle("C")])
    assert len(groups) == 1
    assert groups[0].cycle_ids == ["A", "B", "C"]


def test_different_settings_form_separate_groups():
    groups = group_cycles_by_settings([_cycle("A"), _cycle("B", speed=900.0)])
    assert len(groups) == 2
    assert [group.cycle_ids for group in groups] == [["A"], ["B"]]


def test_group_order_follows_first_appearance():
    groups = group_cycles_by_settings([_cycle("A", 900.0), _cycle("B", 820.0), _cycle("C", 900.0)])
    assert groups[0].cycle_ids == ["A", "C"]
    assert groups[1].cycle_ids == ["B"]


def test_group_serializes_settings_and_ids():
    payload = group_cycles_by_settings([_cycle("A")])[0].to_dict()
    assert payload["cycle_ids"] == ["A"]
    assert payload["settings"]["target_speed"] == 820.0
    assert payload["cycle_count"] == 1


from app.services.group_analysis.statistics import (
    process_capability,
    summarize_features,
)


class _Features:
    """FasteningFeatures 대역. 통계 계산에 필요한 필드만 갖는다."""

    def __init__(self, final_torque: float, total_time: float = 500.0) -> None:
        self.final_torque = final_torque
        self.total_time = total_time
        self.overshoot_percent = 2.0
        self.waveform_stability_score = 0.8


def test_summarize_reports_mean_and_spread():
    summary = summarize_features(
        [_Features(1.0), _Features(2.0), _Features(3.0)],
        feature_names=["final_torque"],
    )
    dist = summary["final_torque"]
    assert dist.mean == 2.0
    assert dist.min == 1.0
    assert dist.max == 3.0
    assert dist.count == 3
    assert dist.std > 0.0


def test_summarize_single_cycle_has_zero_std():
    summary = summarize_features([_Features(1.5)], feature_names=["final_torque"])
    assert summary["final_torque"].std == 0.0
    assert summary["final_torque"].p05 == 1.5
    assert summary["final_torque"].p95 == 1.5


def test_summarize_serializes():
    payload = summarize_features([_Features(1.0)], feature_names=["final_torque"])[
        "final_torque"
    ].to_dict()
    assert payload["feature"] == "final_torque"
    assert payload["count"] == 1


def test_capability_is_high_when_spread_is_tiny():
    values = [1.20, 1.201, 1.199, 1.2005]
    assert process_capability(values, 1.16, 1.24) > 3.0


def test_capability_is_low_when_spread_is_wide():
    values = [1.10, 1.30, 1.15, 1.28]
    assert process_capability(values, 1.16, 1.24) < 1.0


def test_capability_with_zero_spread_is_capped():
    assert process_capability([1.2, 1.2, 1.2], 1.16, 1.24) == 10.0


def test_capability_with_insufficient_samples_returns_zero():
    assert process_capability([1.2], 1.16, 1.24) == 0.0

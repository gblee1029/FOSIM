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

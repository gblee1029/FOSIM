from __future__ import annotations

import pandas as pd
import pytest

from app.services.import_service.sample_data import synthetic_waveform
from app.services.optimization.optimizer import (
    OptimizationObjectives,
    confidence_grade,
    optimize_candidates,
)
from app.services.simulation.simulator import FasteningSettings


def _settings() -> FasteningSettings:
    return FasteningSettings(
        target_speed=820.0,
        target_torque=1.2,
        clamp_rising_time=100.0,
        torque_hold_time=30.0,
    )


def _objectives() -> OptimizationObjectives:
    return OptimizationObjectives(
        target_torque_min=1.14,
        target_torque_max=1.26,
        max_overshoot_percent=8.0,
        max_fastening_time=900.0,
        min_stability_score=0.5,
    )


def _scaled_waveform(factor: float) -> pd.DataFrame:
    frame = synthetic_waveform().copy()
    frame["torque"] = frame["torque"] * factor
    return frame


def test_single_waveform_matches_previous_behavior():
    waveform = synthetic_waveform()
    result = optimize_candidates([waveform], _settings(), _objectives())
    assert result.recommended
    assert all(len(item.per_cycle) == 1 for item in result.recommended)


def test_every_candidate_is_evaluated_on_every_cycle():
    waveforms = [_scaled_waveform(1.0), _scaled_waveform(1.02), _scaled_waveform(0.98)]
    result = optimize_candidates(waveforms, _settings(), _objectives())
    assert result.recommended
    for candidate in result.recommended:
        assert len(candidate.per_cycle) == 3


def test_small_group_uses_worst_case_gate():
    waveforms = [_scaled_waveform(1.0), _scaled_waveform(1.02)]
    result = optimize_candidates(waveforms, _settings(), _objectives())
    assert result.recommended[0].gate_mode == "worst"


def test_rejection_records_which_cycle_failed():
    strict = OptimizationObjectives(
        target_torque_min=1.199,
        target_torque_max=1.201,
        max_overshoot_percent=0.01,
        max_fastening_time=1.0,
        min_stability_score=0.999,
    )
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), strict)
    assert result.rejected_count > 0
    assert result.rejection_details
    assert "cycle_id" in result.rejection_details[0]


def test_empty_waveform_list_is_rejected():
    with pytest.raises(ValueError):
        optimize_candidates([], _settings(), _objectives())


@pytest.mark.parametrize(
    "count,grade",
    [(1, "reference"), (4, "reference"), (5, "moderate"), (19, "moderate"), (20, "statistical")],
)
def test_confidence_grade_thresholds(count: int, grade: str):
    assert confidence_grade(count) == grade

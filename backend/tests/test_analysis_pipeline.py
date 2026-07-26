import math

import pandas as pd

from app.services.feature_extraction.features import extract_features
from app.services.optimization.optimizer import OptimizationObjectives, optimize_candidates
from app.services.segmentation.segments import detect_segments
from app.services.simulation.simulator import FasteningSettings, simulate_waveform


def make_waveform() -> pd.DataFrame:
    rows = []
    for idx in range(0, 241):
        t = float(idx * 2)
        if t < 80:
            torque = 0.03 + 0.0002 * t
            speed = 820 * (1 - math.exp(-t / 24))
            angle = t * 0.09
        elif t < 150:
            torque = 0.08 + (t - 80) * 0.003
            speed = 790 - (t - 80) * 1.3
            angle = 7.2 + (t - 80) * 0.08
        elif t < 285:
            torque = 0.31 + (1.2 - 0.31) * (1 - math.exp(-(t - 150) / 58))
            speed = 610 - (t - 150) * 1.5
            angle = 12.8 + (t - 150) * 0.05
        elif t < 335:
            torque = 1.22 + 0.02 * math.sin((t - 285) / 6)
            speed = max(0.0, 170 - (t - 285) * 3)
            angle = 19.5 + (t - 285) * 0.01
        else:
            torque = max(0.22, 1.12 * math.exp(-(t - 335) / 110))
            speed = 0.0
            angle = 20.0
        rows.append(
            {
                "cycle_id": "CYCLE-TEST",
                "sample_index": idx,
                "time_ms": t,
                "torque": torque,
                "speed": speed,
                "angle": angle,
                "current": 0.2 + torque * 0.8,
                "event_code": "",
            }
        )
    return pd.DataFrame(rows)


def test_detect_segments_finds_seating_clamp_hold_order():
    waveform = make_waveform()
    settings = FasteningSettings(
        target_speed=820,
        target_torque=1.2,
        clamp_rising_time=110,
        torque_hold_time=40,
    )

    segments = detect_segments(waveform, settings)

    assert 120 <= segments.seating_time <= 190
    assert segments.seating_time < segments.target_reach_time < segments.hold_end_time
    assert segments.stop_time >= segments.hold_end_time
    assert segments.confidence >= 0.65


def test_extract_features_reports_expected_torque_metrics():
    waveform = make_waveform()
    settings = FasteningSettings(
        target_speed=820,
        target_torque=1.2,
        clamp_rising_time=110,
        torque_hold_time=40,
    )
    segments = detect_segments(waveform, settings)

    features = extract_features(waveform, segments, settings)

    assert features.final_torque > 0.2
    assert 0 <= features.overshoot_percent <= 5
    assert features.clamp_time > 40
    assert features.clamp_gradient > 0
    assert 0 <= features.waveform_stability_score <= 1


def test_simulation_changes_clamp_rising_time_and_reduces_overshoot():
    waveform = make_waveform()
    current = FasteningSettings(
        target_speed=820,
        target_torque=1.2,
        clamp_rising_time=100,
        torque_hold_time=30,
    )
    candidate = FasteningSettings(
        target_speed=760,
        target_torque=1.2,
        clamp_rising_time=160,
        torque_hold_time=50,
    )

    result = simulate_waveform(waveform, current, candidate)

    assert result.predicted_features.clamp_time > result.current_features.clamp_time
    assert (
        result.predicted_features.overshoot_percent
        <= result.current_features.overshoot_percent
    )
    assert len(result.predicted_waveform) > 100
    assert result.confidence.level in {"high", "medium", "low"}


def test_optimizer_returns_three_purpose_built_candidates():
    waveform = make_waveform()
    settings = FasteningSettings(
        target_speed=820,
        target_torque=1.2,
        clamp_rising_time=100,
        torque_hold_time=30,
    )
    objectives = OptimizationObjectives(
        target_torque_min=1.16,
        target_torque_max=1.24,
        max_overshoot_percent=4.0,
        max_fastening_time=620,
    )

    result = optimize_candidates(waveform, settings, objectives)

    labels = {candidate.label for candidate in result.recommended}
    assert labels == {"quality_stable", "cycle_time", "minimum_change"}
    assert all(candidate.score >= 0 for candidate in result.recommended)
    assert result.evaluated_count > 0

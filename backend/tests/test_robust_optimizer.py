from __future__ import annotations

import pandas as pd
import pytest

from app.services.import_service.sample_data import synthetic_waveform
from app.services.optimization.optimizer import (
    OptimizationObjectives,
    confidence_grade,
    optimize_candidates,
)
from app.services.simulation.simulator import (
    FasteningSettings,
    prepare_waveform,
    simulate_prepared,
    simulate_waveform,
)


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


def test_score_breakdown_has_new_keys_and_sums_to_score():
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), _objectives())
    breakdown = result.recommended[0].score_breakdown
    assert set(breakdown) == {
        "constraint",
        "torque_accuracy",
        "reproducibility",
        "overshoot",
        "stability",
        "fastening_time",
        "setting_change",
    }
    assert result.recommended[0].score == pytest.approx(sum(breakdown.values()))


def test_score_never_exceeds_one_hundred():
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), _objectives())
    for candidate in result.all_candidates:
        assert candidate.score <= 100.0 + 1e-6


def test_single_cycle_gets_full_reproducibility():
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), _objectives())
    assert result.recommended[0].score_breakdown["reproducibility"] == pytest.approx(20.0)


def _feature_values(features) -> dict[str, float]:
    return {
        name: getattr(features, name)
        for name in vars(features)
        if isinstance(getattr(features, name), float)
    }


def test_prepared_simulation_matches_the_one_shot_path():
    """전처리를 재사용해도 단발 호출과 완전히 같은 결과여야 한다."""
    waveform = _scaled_waveform(1.0)
    candidate = FasteningSettings(
        target_speed=760.0,
        target_torque=1.2,
        clamp_rising_time=140.0,
        torque_hold_time=50.0,
    )
    direct = simulate_waveform(waveform, _settings(), candidate)
    prepared = prepare_waveform(waveform, _settings())
    reused = simulate_prepared(prepared, _settings(), candidate)

    assert _feature_values(reused.predicted_features) == _feature_values(direct.predicted_features)
    assert reused.confidence.score == direct.confidence.score
    assert len(reused.predicted_waveform) == len(direct.predicted_waveform)


def test_preparation_is_reusable_across_candidates():
    """같은 prepared 객체를 여러 후보에 써도 서로 오염되지 않는다."""
    waveform = _scaled_waveform(1.0)
    prepared = prepare_waveform(waveform, _settings())
    first = FasteningSettings(
        target_speed=700.0, target_torque=1.2, clamp_rising_time=200.0, torque_hold_time=60.0
    )
    second = FasteningSettings(
        target_speed=900.0, target_torque=1.2, clamp_rising_time=60.0, torque_hold_time=10.0
    )
    simulate_prepared(prepared, _settings(), first)
    after = simulate_prepared(prepared, _settings(), second)
    fresh = simulate_waveform(waveform, _settings(), second)
    assert _feature_values(after.predicted_features) == _feature_values(fresh.predicted_features)


def test_stored_simulation_equals_a_fresh_full_simulation():
    """최적화기가 담아 돌려주는 시뮬레이션은 새로 계산한 것과 같아야 한다.

    per_cycle은 입력 파형 순서를 유지하므로 위치로 대조한다. cycle_id로 찾으면
    같은 id를 가진 파형이 섞였을 때 엉뚱한 사이클과 비교하게 된다.
    """
    waveforms = [_scaled_waveform(1.0), _scaled_waveform(1.02), _scaled_waveform(0.98)]
    result = optimize_candidates(waveforms, _settings(), _objectives())
    for candidate in result.recommended:
        assert len(candidate.per_cycle) == len(waveforms)
        for frame, evaluation in zip(waveforms, candidate.per_cycle):
            fresh = simulate_waveform(frame, _settings(), candidate.settings)
            assert _feature_values(evaluation.simulation.predicted_features) == _feature_values(
                fresh.predicted_features
            )

        worst = max(
            candidate.per_cycle,
            key=lambda item: item.simulation.predicted_features.overshoot_percent,
        )
        assert _feature_values(candidate.simulation.predicted_features) == _feature_values(
            worst.simulation.predicted_features
        )


def test_recommended_candidates_carry_a_predicted_waveform():
    """예측 파형 생성을 미뤄도 추천 후보에는 반드시 파형이 실려 있어야 한다."""
    waveforms = [_scaled_waveform(1.0), _scaled_waveform(1.02)]
    result = optimize_candidates(waveforms, _settings(), _objectives())
    for candidate in result.recommended:
        assert len(candidate.simulation.predicted_waveform) > 0


def test_tight_group_scores_reproducibility_above_scattered_group():
    tight = [_scaled_waveform(1.0), _scaled_waveform(1.001), _scaled_waveform(0.999)]
    scattered = [_scaled_waveform(1.0), _scaled_waveform(1.20), _scaled_waveform(0.80)]
    tight_result = optimize_candidates(tight, _settings(), _objectives())
    scattered_result = optimize_candidates(scattered, _settings(), _objectives())
    tight_score = tight_result.all_candidates[0].score_breakdown["reproducibility"]
    scattered_score = scattered_result.all_candidates[0].score_breakdown["reproducibility"]
    assert tight_score > scattered_score

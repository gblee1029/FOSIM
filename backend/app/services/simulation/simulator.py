from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FasteningSettings:
    target_speed: float
    target_torque: float
    clamp_rising_time: float
    torque_hold_time: float
    seating_sensitivity: float | None = None
    speed_adjust_time: float | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "FasteningSettings":
        return cls(
            target_speed=float(value["target_speed"]),
            target_torque=float(value["target_torque"]),
            clamp_rising_time=float(value["clamp_rising_time"]),
            torque_hold_time=float(value["torque_hold_time"]),
            seating_sensitivity=_optional_float(value.get("seating_sensitivity")),
            speed_adjust_time=_optional_float(value.get("speed_adjust_time")),
        )

    def to_dict(self) -> dict[str, float | None]:
        return asdict(self)


@dataclass(frozen=True)
class SimulationConfidence:
    level: str
    score: float
    factors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimulationResult:
    simulation_type: str
    source_cycle_id: str
    current_settings: FasteningSettings
    candidate_settings: FasteningSettings
    setting_changes: dict[str, float]
    current_features: Any
    predicted_features: Any
    confidence: SimulationConfidence
    warnings: list[str]
    predicted_waveform: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_type": self.simulation_type,
            "source_cycle_id": self.source_cycle_id,
            "current_settings": self.current_settings.to_dict(),
            "candidate_settings": self.candidate_settings.to_dict(),
            "setting_changes": self.setting_changes,
            "current_features": self.current_features.to_dict(),
            "predicted_features": self.predicted_features.to_dict(),
            "confidence": self.confidence.to_dict(),
            "warnings": self.warnings,
            "predicted_waveform": self.predicted_waveform,
        }


@dataclass(frozen=True)
class PreparedWaveform:
    """후보와 무관한 전처리 결과.

    정규화·구간분할·특징추출은 관측 파형과 현재 설정에만 의존하므로 후보마다
    다시 계산할 필요가 없다. 후보 수만큼 반복하면 최적화 비용의 대부분을
    같은 계산에 쓰게 되어, 한 번 만들어 재사용한다.
    """

    clean: pd.DataFrame
    segments: Any
    current_features: Any


def prepare_waveform(
    waveform: pd.DataFrame,
    current_settings: FasteningSettings,
) -> PreparedWaveform:
    from app.services.feature_extraction.features import extract_features
    from app.services.segmentation.segments import detect_segments

    clean = _normalize_waveform(waveform)
    segments = detect_segments(clean, current_settings)
    return PreparedWaveform(
        clean=clean,
        segments=segments,
        current_features=extract_features(clean, segments, current_settings),
    )


def simulate_waveform(
    waveform: pd.DataFrame,
    current_settings: FasteningSettings,
    candidate_settings: FasteningSettings,
) -> SimulationResult:
    return simulate_prepared(
        prepare_waveform(waveform, current_settings),
        current_settings,
        candidate_settings,
    )


def simulate_prepared(
    prepared: PreparedWaveform,
    current_settings: FasteningSettings,
    candidate_settings: FasteningSettings,
    with_waveform: bool = True,
) -> SimulationResult:
    """준비된 파형으로 후보 하나를 시뮬레이션한다.

    `with_waveform=False`는 예측 파형 생성을 건너뛴다. 후보 탐색 중에는 점수에
    쓰이는 예측 특징만 필요하고 파형은 화면 표시용이므로, 최종 후보에 대해서만
    다시 생성하면 된다.
    """
    from app.services.feature_extraction.features import FasteningFeatures

    clean = prepared.clean
    segments = prepared.segments
    current_features = prepared.current_features
    setting_changes = _setting_changes(current_settings, candidate_settings)
    warnings = _simulation_warnings(setting_changes, current_features)

    speed_factor = _bounded_ratio(
        current_settings.target_speed,
        candidate_settings.target_speed,
        0.75,
        1.35,
    )
    clamp_factor = _bounded_ratio(
        candidate_settings.clamp_rising_time,
        current_settings.clamp_rising_time,
        0.5,
        2.0,
    )
    target_ratio = _bounded_ratio(
        candidate_settings.target_torque,
        current_settings.target_torque,
        0.85,
        1.15,
    )

    predicted_clamp_time = max(8.0, current_features.clamp_time * clamp_factor)
    pre_target_shift = max(0.0, segments.seating_time) * (speed_factor - 1.0)
    predicted_total_time = max(
        predicted_clamp_time + candidate_settings.torque_hold_time + 40.0,
        current_features.total_time
        + pre_target_shift
        + (predicted_clamp_time - current_features.clamp_time)
        + (candidate_settings.torque_hold_time - current_settings.torque_hold_time),
    )
    predicted_overshoot = _predict_overshoot(
        current_features.overshoot_percent,
        speed_factor,
        clamp_factor,
        target_ratio,
    )
    predicted_peak = candidate_settings.target_torque * (
        1.0 + predicted_overshoot / 100.0
    )
    predicted_final = candidate_settings.target_torque * (
        1.0 - min(0.03, abs(candidate_settings.torque_hold_time - 30.0) / 6000.0)
    )
    predicted_clamp_gradient = (
        candidate_settings.target_torque - current_features.seating_torque
    ) / max(predicted_clamp_time, 1.0)
    predicted_stability = _predict_stability(
        current_features.waveform_stability_score,
        clamp_factor,
        candidate_settings.torque_hold_time,
        current_settings.torque_hold_time,
    )

    predicted_features = FasteningFeatures(
        total_time=predicted_total_time,
        max_torque=predicted_peak,
        final_torque=predicted_final,
        mean_torque=current_features.mean_torque * target_ratio,
        torque_std=current_features.torque_std,
        torque_rms=current_features.torque_rms * target_ratio,
        torque_peak_to_peak=predicted_peak - min(current_features.final_torque, 0.0),
        torque_integral=current_features.torque_integral * target_ratio,
        max_speed=candidate_settings.target_speed,
        mean_speed=current_features.mean_speed / max(speed_factor, 0.1),
        total_angle=current_features.total_angle,
        total_turns=current_features.total_turns,
        free_run_time=current_features.free_run_time * speed_factor,
        free_run_torque_mean=current_features.free_run_torque_mean,
        free_run_torque_std=current_features.free_run_torque_std,
        free_run_torque_rms=current_features.free_run_torque_rms,
        free_run_peak_count=current_features.free_run_peak_count,
        free_run_vibration_energy=current_features.free_run_vibration_energy,
        engage_start_time=current_features.engage_start_time * speed_factor,
        engage_end_time=current_features.engage_end_time * speed_factor,
        engage_duration=current_features.engage_duration * speed_factor,
        engage_start_torque=current_features.engage_start_torque,
        engage_end_torque=current_features.engage_end_torque,
        engage_gradient=current_features.engage_gradient / max(speed_factor, 0.1),
        engage_peak_count=current_features.engage_peak_count,
        engage_speed_drop=current_features.engage_speed_drop,
        seating_time=current_features.seating_time * speed_factor,
        seating_torque=current_features.seating_torque,
        seating_angle=current_features.seating_angle,
        seating_speed=candidate_settings.target_speed * 0.72,
        pre_seating_gradient=current_features.pre_seating_gradient,
        post_seating_gradient=predicted_clamp_gradient,
        seating_impact_peak=max(
            current_features.seating_torque,
            current_features.seating_impact_peak
            * (1.0 - max(0.0, speed_factor - 1.0) * 0.25),
        ),
        seating_confidence=current_features.seating_confidence,
        clamp_start_time=current_features.seating_time * speed_factor,
        target_reach_time=current_features.seating_time * speed_factor
        + predicted_clamp_time,
        clamp_time=predicted_clamp_time,
        clamp_start_torque=current_features.seating_torque,
        clamp_end_torque=candidate_settings.target_torque,
        clamp_gradient=predicted_clamp_gradient,
        clamp_gradient_linearity=min(1.0, current_features.clamp_gradient_linearity),
        clamp_angle=current_features.clamp_angle * clamp_factor,
        clamp_peak_count=current_features.clamp_peak_count,
        clamp_oscillation=current_features.clamp_oscillation
        * (1.0 / max(clamp_factor, 0.6)),
        hold_time=candidate_settings.torque_hold_time,
        hold_mean_torque=predicted_final,
        hold_std=current_features.hold_std
        * (0.9 if candidate_settings.torque_hold_time >= current_settings.torque_hold_time else 1.1),
        hold_peak_to_peak=current_features.hold_peak_to_peak,
        hold_decay_rate=current_features.hold_decay_rate,
        hold_vibration_energy=current_features.hold_vibration_energy,
        target_error=predicted_final - candidate_settings.target_torque,
        peak_torque=predicted_peak,
        overshoot_percent=predicted_overshoot,
        undershoot_percent=max(
            0.0,
            (candidate_settings.target_torque - predicted_final)
            / max(candidate_settings.target_torque, 0.001)
            * 100.0,
        ),
        waveform_stability_score=predicted_stability,
        anomaly_score=max(0.0, min(1.0, 1.0 - predicted_stability)),
    )

    predicted_waveform = (
        _generate_predicted_waveform(
            clean,
            current_features,
            predicted_features,
            candidate_settings,
        )
        if with_waveform
        else []
    )
    confidence = _confidence(setting_changes, current_features, clean, warnings)
    return SimulationResult(
        simulation_type="rule_based",
        source_cycle_id=str(clean["cycle_id"].iloc[0]) if "cycle_id" in clean else "",
        current_settings=current_settings,
        candidate_settings=candidate_settings,
        setting_changes=setting_changes,
        current_features=current_features,
        predicted_features=predicted_features,
        confidence=confidence,
        warnings=warnings,
        predicted_waveform=predicted_waveform,
    )


def _normalize_waveform(waveform: pd.DataFrame) -> pd.DataFrame:
    clean = waveform.copy()
    clean = clean.sort_values("time_ms").drop_duplicates("time_ms")
    for column in ("torque", "speed", "angle", "current"):
        if column not in clean:
            clean[column] = np.nan
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    clean["time_ms"] = pd.to_numeric(clean["time_ms"], errors="coerce")
    clean = clean.dropna(subset=["time_ms", "torque"]).reset_index(drop=True)
    clean["speed"] = clean["speed"].interpolate(limit_direction="both").fillna(0.0)
    clean["angle"] = clean["angle"].interpolate(limit_direction="both").fillna(0.0)
    clean["current"] = clean["current"].interpolate(limit_direction="both").fillna(0.0)
    if "sample_index" not in clean:
        clean["sample_index"] = range(len(clean))
    if "cycle_id" not in clean:
        clean["cycle_id"] = "CYCLE"
    return clean


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _bounded_ratio(numerator: float, denominator: float, low: float, high: float) -> float:
    if denominator == 0:
        return 1.0
    return float(np.clip(numerator / denominator, low, high))


def _setting_changes(
    current: FasteningSettings, candidate: FasteningSettings
) -> dict[str, float]:
    current_dict = current.to_dict()
    candidate_dict = candidate.to_dict()
    changes: dict[str, float] = {}
    for key, current_value in current_dict.items():
        candidate_value = candidate_dict.get(key)
        if current_value is None or candidate_value is None:
            continue
        changes[key] = float(candidate_value) - float(current_value)
    return changes


def _predict_overshoot(
    current_overshoot: float,
    speed_factor: float,
    clamp_factor: float,
    target_ratio: float,
) -> float:
    overshoot = max(current_overshoot, 0.8)
    if speed_factor > 1.0:
        overshoot *= 1.0 - min(0.28, (speed_factor - 1.0) * 0.55)
    else:
        overshoot *= 1.0 + min(0.22, (1.0 - speed_factor) * 0.45)
    if clamp_factor > 1.0:
        overshoot *= 1.0 - min(0.45, (clamp_factor - 1.0) * 0.55)
    else:
        overshoot *= 1.0 + min(0.55, (1.0 - clamp_factor) * 0.75)
    overshoot *= 1.0 + max(0.0, target_ratio - 1.0) * 0.25
    return float(np.clip(overshoot, 0.0, 20.0))


def _predict_stability(
    current_score: float,
    clamp_factor: float,
    candidate_hold_time: float,
    current_hold_time: float,
) -> float:
    score = current_score
    if clamp_factor >= 1.0:
        score += min(0.12, (clamp_factor - 1.0) * 0.12)
    else:
        score -= min(0.18, (1.0 - clamp_factor) * 0.18)
    if candidate_hold_time >= current_hold_time:
        score += min(0.08, (candidate_hold_time - current_hold_time) / 400.0)
    else:
        score -= min(0.08, (current_hold_time - candidate_hold_time) / 400.0)
    return float(np.clip(score, 0.0, 1.0))


def _generate_predicted_waveform(
    source: pd.DataFrame,
    current_features: Any,
    predicted_features: Any,
    settings: FasteningSettings,
) -> list[dict[str, Any]]:
    dt = _median_dt(source)
    total_time = max(predicted_features.total_time, predicted_features.target_reach_time + 40)
    times = np.arange(0.0, total_time + dt, dt)
    seating_time = predicted_features.seating_time
    target_time = predicted_features.target_reach_time
    hold_end = target_time + max(settings.torque_hold_time, dt)
    torque: list[float] = []
    speed: list[float] = []
    angle: list[float] = []
    angle_value = 0.0
    seating_torque = max(0.02, predicted_features.seating_torque)
    target_torque = settings.target_torque
    for t in times:
        if t < seating_time:
            p = t / max(seating_time, dt)
            torque_value = 0.03 + (seating_torque - 0.03) * (p**2.0)
            speed_value = settings.target_speed * (1 - np.exp(-t / 28.0))
        elif t < target_time:
            p = (t - seating_time) / max(target_time - seating_time, dt)
            k = 3.3
            curve = (1 - np.exp(-k * p)) / (1 - np.exp(-k))
            torque_value = seating_torque + (target_torque - seating_torque) * curve
            speed_value = max(40.0, settings.target_speed * (1.0 - 0.82 * p))
        elif t < hold_end:
            p = (t - target_time) / max(hold_end - target_time, dt)
            oscillation = np.sin(p * np.pi * 4) * predicted_features.hold_std
            torque_value = predicted_features.hold_mean_torque + oscillation
            speed_value = max(0.0, 90.0 * (1.0 - p))
        else:
            p = (t - hold_end) / max(total_time - hold_end, dt)
            torque_value = max(0.05, predicted_features.hold_mean_torque * np.exp(-p * 2.8))
            speed_value = 0.0
        angle_value += max(speed_value, 0.0) * 0.006 * dt
        torque.append(float(max(0.0, torque_value)))
        speed.append(float(max(0.0, speed_value)))
        angle.append(float(angle_value))

    peak_index = int(np.argmax(torque)) if torque else 0
    if torque and predicted_features.peak_torque > max(torque):
        torque[peak_index] = float(predicted_features.peak_torque)

    return [
        {
            "cycle_id": str(source["cycle_id"].iloc[0]) if "cycle_id" in source else "PREDICTED",
            "sample_index": index,
            "time_ms": float(t),
            "torque": float(torque[index]),
            "speed": float(speed[index]),
            "angle": float(angle[index]),
            "current": float(0.2 + torque[index] * 0.8),
            "event_code": "SIM",
        }
        for index, t in enumerate(times)
    ]


def _median_dt(waveform: pd.DataFrame) -> float:
    deltas = waveform["time_ms"].diff().dropna()
    if deltas.empty:
        return 2.0
    return float(np.clip(deltas.median(), 1.0, 20.0))


def _simulation_warnings(
    changes: dict[str, float], current_features: Any
) -> list[str]:
    warnings: list[str] = []
    if abs(changes.get("target_torque", 0.0)) > 0.0001:
        warnings.append("Target Torque changed; verify product torque limits before applying.")
    if abs(changes.get("clamp_rising_time", 0.0)) > 60:
        warnings.append("Clamp Rising Time change is large; prediction is reference only.")
    if current_features.seating_confidence < 0.7:
        warnings.append("Seating detection confidence is below the preferred range.")
    return warnings


def _confidence(
    changes: dict[str, float],
    features: Any,
    waveform: pd.DataFrame,
    warnings: list[str],
) -> SimulationConfidence:
    score = 0.88
    factors: list[str] = []
    if waveform["speed"].isna().all():
        score -= 0.15
        factors.append("Speed channel is missing.")
    if waveform["angle"].isna().all():
        score -= 0.12
        factors.append("Angle channel is missing.")
    if features.seating_confidence < 0.75:
        score -= 0.16
        factors.append("Seating point is not sharply detected.")
    for key, delta in changes.items():
        if key in {"target_speed", "target_torque"}:
            reference = max(abs(getattr(features, "final_torque", 1.0)), 1.0)
        else:
            reference = 100.0
        if abs(delta) / reference > 0.5:
            score -= 0.08
            factors.append(f"{key} change is relatively large.")
    if warnings:
        score -= min(0.12, len(warnings) * 0.04)
    score = float(np.clip(score, 0.0, 1.0))
    level = "high" if score >= 0.78 else "medium" if score >= 0.55 else "low"
    if not factors:
        factors.append("Setting changes are within the MVP rule model range.")
    return SimulationConfidence(level=level, score=score, factors=factors)

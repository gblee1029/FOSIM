from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.services.segmentation.segments import SegmentResult
from app.services.simulation.simulator import FasteningSettings


@dataclass(frozen=True)
class FasteningFeatures:
    total_time: float
    max_torque: float
    final_torque: float
    mean_torque: float
    torque_std: float
    torque_rms: float
    torque_peak_to_peak: float
    torque_integral: float
    max_speed: float
    mean_speed: float
    total_angle: float
    total_turns: float
    free_run_time: float
    free_run_torque_mean: float
    free_run_torque_std: float
    free_run_torque_rms: float
    free_run_peak_count: int
    free_run_vibration_energy: float
    engage_start_time: float
    engage_end_time: float
    engage_duration: float
    engage_start_torque: float
    engage_end_torque: float
    engage_gradient: float
    engage_peak_count: int
    engage_speed_drop: float
    seating_time: float
    seating_torque: float
    seating_angle: float
    seating_speed: float
    pre_seating_gradient: float
    post_seating_gradient: float
    seating_impact_peak: float
    seating_confidence: float
    clamp_start_time: float
    target_reach_time: float
    clamp_time: float
    clamp_start_torque: float
    clamp_end_torque: float
    clamp_gradient: float
    clamp_gradient_linearity: float
    clamp_angle: float
    clamp_peak_count: int
    clamp_oscillation: float
    hold_time: float
    hold_mean_torque: float
    hold_std: float
    hold_peak_to_peak: float
    hold_decay_rate: float
    hold_vibration_energy: float
    target_error: float
    peak_torque: float
    overshoot_percent: float
    undershoot_percent: float
    waveform_stability_score: float
    anomaly_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_features(
    waveform: pd.DataFrame,
    segments: SegmentResult,
    settings: FasteningSettings,
) -> FasteningFeatures:
    clean = waveform.sort_values("time_ms").reset_index(drop=True)
    full = clean
    free = _slice(clean, segments.start_time, segments.free_run_end_time)
    engage = _slice(clean, segments.engage_start_time, segments.seating_time)
    clamp = _slice(clean, segments.seating_time, segments.target_reach_time)
    hold = _slice(clean, segments.target_reach_time, segments.hold_end_time)
    seating_row = _nearest(clean, segments.seating_time)
    target_row = _nearest(clean, segments.target_reach_time)
    hold_end_row = _nearest(clean, segments.hold_end_time)

    torque = full["torque"].astype(float)
    speed = _series(full, "speed")
    angle = _series(full, "angle")
    max_torque = float(torque.max())
    peak_torque = max_torque
    final_torque = float(hold["torque"].mean()) if not hold.empty else float(hold_end_row["torque"])
    target_error = final_torque - settings.target_torque
    overshoot_percent = max(0.0, (peak_torque - settings.target_torque) / max(settings.target_torque, 0.001) * 100.0)
    undershoot_percent = max(0.0, (settings.target_torque - final_torque) / max(settings.target_torque, 0.001) * 100.0)
    clamp_gradient = (
        float(target_row["torque"]) - float(seating_row["torque"])
    ) / max(segments.target_reach_time - segments.seating_time, 1.0)
    hold_std = _std(hold["torque"]) if not hold.empty else 0.0
    clamp_oscillation = _std(clamp["torque"] - _linear_fit(clamp)) if len(clamp) >= 3 else 0.0
    stability = _stability_score(overshoot_percent, clamp_oscillation, hold_std, settings.target_torque)

    return FasteningFeatures(
        total_time=float(segments.stop_time - segments.start_time),
        max_torque=max_torque,
        final_torque=final_torque,
        mean_torque=float(torque.mean()),
        torque_std=_std(torque),
        torque_rms=float(np.sqrt(np.mean(np.square(torque)))),
        torque_peak_to_peak=float(torque.max() - torque.min()),
        torque_integral=float(np.trapezoid(torque, full["time_ms"].astype(float))),
        max_speed=float(speed.max()) if not speed.empty else 0.0,
        mean_speed=float(speed.mean()) if not speed.empty else 0.0,
        total_angle=float(angle.max() - angle.min()) if not angle.empty else 0.0,
        total_turns=float((angle.max() - angle.min()) / 360.0) if not angle.empty else 0.0,
        free_run_time=max(0.0, segments.free_run_end_time - segments.start_time),
        free_run_torque_mean=_mean(free["torque"]),
        free_run_torque_std=_std(free["torque"]),
        free_run_torque_rms=_rms(free["torque"]),
        free_run_peak_count=_peak_count(free["torque"]),
        free_run_vibration_energy=_vibration_energy(free["torque"]),
        engage_start_time=segments.engage_start_time,
        engage_end_time=segments.seating_time,
        engage_duration=max(0.0, segments.seating_time - segments.engage_start_time),
        engage_start_torque=float(_nearest(clean, segments.engage_start_time)["torque"]),
        engage_end_torque=float(seating_row["torque"]),
        engage_gradient=_gradient_between(clean, segments.engage_start_time, segments.seating_time),
        engage_peak_count=_peak_count(engage["torque"]),
        engage_speed_drop=_speed_drop(engage),
        seating_time=segments.seating_time,
        seating_torque=float(seating_row["torque"]),
        seating_angle=float(seating_row.get("angle", 0.0)),
        seating_speed=float(seating_row.get("speed", 0.0)),
        pre_seating_gradient=_gradient_between(clean, max(segments.start_time, segments.seating_time - 30), segments.seating_time),
        post_seating_gradient=_gradient_between(clean, segments.seating_time, min(segments.target_reach_time, segments.seating_time + 30)),
        seating_impact_peak=float(_slice(clean, segments.seating_time, segments.seating_time + 24)["torque"].max()),
        seating_confidence=segments.confidence,
        clamp_start_time=segments.seating_time,
        target_reach_time=segments.target_reach_time,
        clamp_time=max(0.0, segments.target_reach_time - segments.seating_time),
        clamp_start_torque=float(seating_row["torque"]),
        clamp_end_torque=float(target_row["torque"]),
        clamp_gradient=clamp_gradient,
        clamp_gradient_linearity=_linearity(clamp),
        clamp_angle=_angle_delta(clamp),
        clamp_peak_count=_peak_count(clamp["torque"]),
        clamp_oscillation=clamp_oscillation,
        hold_time=max(0.0, segments.hold_end_time - segments.target_reach_time),
        hold_mean_torque=_mean(hold["torque"]),
        hold_std=hold_std,
        hold_peak_to_peak=_peak_to_peak(hold["torque"]),
        hold_decay_rate=_gradient_between(clean, segments.target_reach_time, segments.hold_end_time),
        hold_vibration_energy=_vibration_energy(hold["torque"]),
        target_error=target_error,
        peak_torque=peak_torque,
        overshoot_percent=overshoot_percent,
        undershoot_percent=undershoot_percent,
        waveform_stability_score=stability,
        anomaly_score=float(np.clip(1.0 - stability + min(overshoot_percent / 30.0, 0.4), 0.0, 1.0)),
    )


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(dtype=float)
    return frame[column].astype(float)


def _slice(frame: pd.DataFrame, start: float, end: float) -> pd.DataFrame:
    sliced = frame[(frame["time_ms"] >= start) & (frame["time_ms"] <= end)]
    return sliced.copy()


def _nearest(frame: pd.DataFrame, time_ms: float) -> pd.Series:
    index = (frame["time_ms"].astype(float) - time_ms).abs().idxmin()
    return frame.loc[index]


def _mean(series: pd.Series) -> float:
    return float(series.astype(float).mean()) if len(series) else 0.0


def _std(series: pd.Series) -> float:
    return float(series.astype(float).std(ddof=0)) if len(series) else 0.0


def _rms(series: pd.Series) -> float:
    values = series.astype(float).to_numpy()
    return float(np.sqrt(np.mean(np.square(values)))) if len(values) else 0.0


def _peak_to_peak(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    values = series.astype(float)
    return float(values.max() - values.min())


def _vibration_energy(series: pd.Series) -> float:
    values = series.astype(float).to_numpy()
    if len(values) < 3:
        return 0.0
    centered = values - np.mean(values)
    return float(np.mean(np.square(np.diff(centered))))


def _peak_count(series: pd.Series) -> int:
    values = series.astype(float).to_numpy()
    if len(values) < 3:
        return 0
    peaks = 0
    for index in range(1, len(values) - 1):
        if values[index] > values[index - 1] and values[index] > values[index + 1]:
            peaks += 1
    return peaks


def _gradient_between(frame: pd.DataFrame, start: float, end: float) -> float:
    if end <= start:
        return 0.0
    start_row = _nearest(frame, start)
    end_row = _nearest(frame, end)
    return float((end_row["torque"] - start_row["torque"]) / max(end - start, 1.0))


def _speed_drop(frame: pd.DataFrame) -> float:
    if frame.empty or "speed" not in frame:
        return 0.0
    values = frame["speed"].astype(float)
    return float(values.max() - values.iloc[-1])


def _angle_delta(frame: pd.DataFrame) -> float:
    if frame.empty or "angle" not in frame:
        return 0.0
    values = frame["angle"].astype(float)
    return float(values.max() - values.min())


def _linear_fit(frame: pd.DataFrame) -> np.ndarray:
    if len(frame) < 2:
        return np.zeros(len(frame))
    x = frame["time_ms"].astype(float).to_numpy()
    y = frame["torque"].astype(float).to_numpy()
    coefficients = np.polyfit(x - x[0], y, 1)
    return np.polyval(coefficients, x - x[0])


def _linearity(frame: pd.DataFrame) -> float:
    if len(frame) < 4:
        return 1.0
    y = frame["torque"].astype(float).to_numpy()
    fit = _linear_fit(frame)
    ss_res = float(np.sum(np.square(y - fit)))
    ss_tot = float(np.sum(np.square(y - np.mean(y))))
    if ss_tot == 0:
        return 1.0
    return float(np.clip(1.0 - ss_res / ss_tot, 0.0, 1.0))


def _stability_score(
    overshoot_percent: float,
    clamp_oscillation: float,
    hold_std: float,
    target_torque: float,
) -> float:
    overshoot_penalty = min(0.35, overshoot_percent / 35.0)
    clamp_penalty = min(0.25, clamp_oscillation / max(target_torque, 0.001) * 3.0)
    hold_penalty = min(0.25, hold_std / max(target_torque, 0.001) * 4.0)
    return float(np.clip(1.0 - overshoot_penalty - clamp_penalty - hold_penalty, 0.0, 1.0))

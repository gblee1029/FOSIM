from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.services.simulation.simulator import FasteningSettings


@dataclass(frozen=True)
class SegmentResult:
    start_time: float
    free_run_end_time: float
    engage_start_time: float
    seating_time: float
    target_reach_time: float
    hold_end_time: float
    stop_time: float
    confidence: float
    method: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_segments(waveform: pd.DataFrame, settings: FasteningSettings) -> SegmentResult:
    clean = waveform.sort_values("time_ms").reset_index(drop=True).copy()
    time = clean["time_ms"].astype(float).to_numpy()
    torque = clean["torque"].astype(float).to_numpy()
    speed = (
        clean["speed"].astype(float).to_numpy()
        if "speed" in clean
        else np.zeros_like(torque)
    )
    if len(time) < 6:
        raise ValueError("At least 6 waveform samples are required.")

    baseline_count = max(3, min(20, len(torque) // 10))
    baseline = float(np.median(torque[:baseline_count]))
    gradient = np.gradient(torque, time, edge_order=1)
    start_index = _first_index((speed > 15) | (torque > baseline + 0.02), default=0)
    engage_index = _first_index(torque > baseline + max(0.035, settings.target_torque * 0.04), default=start_index)

    seating_threshold = max(baseline + 0.12, settings.target_torque * 0.18)
    gradient_threshold = max(settings.target_torque * 0.0016, np.percentile(gradient, 62))
    seating_candidates = np.where(
        (torque > seating_threshold) & (gradient > gradient_threshold)
    )[0]
    seating_index = _sustained_candidate(seating_candidates, gradient, gradient_threshold)
    if seating_index is None:
        seating_index = _first_index(torque > seating_threshold, default=max(engage_index + 1, start_index + 1))

    target_threshold = settings.target_torque * 0.96
    target_after = np.where((np.arange(len(torque)) > seating_index) & (torque >= target_threshold))[0]
    target_index = int(target_after[0]) if target_after.size else min(len(torque) - 2, seating_index + 3)

    hold_samples = max(2, int(round(settings.torque_hold_time / max(_median_dt(time), 1.0))))
    hold_end_index = min(len(torque) - 1, target_index + hold_samples)
    stop_candidates = np.where((np.arange(len(speed)) > target_index) & (speed < 8))[0]
    stop_index = int(stop_candidates[0]) if stop_candidates.size else len(torque) - 1
    stop_index = max(stop_index, hold_end_index)

    free_run_end_index = max(engage_index, seating_index - 1)
    warnings: list[str] = []
    confidence = 0.88
    if seating_candidates.size == 0:
        confidence -= 0.22
        warnings.append("Seating point used torque threshold fallback.")
    if target_after.size == 0:
        confidence -= 0.18
        warnings.append("Target reach point was estimated because target torque was not crossed.")
    if clean.get("speed") is None:
        confidence -= 0.08
        warnings.append("Speed channel was unavailable.")
    confidence = float(np.clip(confidence, 0.0, 1.0))

    return SegmentResult(
        start_time=float(time[start_index]),
        free_run_end_time=float(time[free_run_end_index]),
        engage_start_time=float(time[engage_index]),
        seating_time=float(time[seating_index]),
        target_reach_time=float(time[target_index]),
        hold_end_time=float(time[hold_end_index]),
        stop_time=float(time[min(stop_index, len(time) - 1)]),
        confidence=confidence,
        method="rule_based",
        warnings=warnings,
    )


def _first_index(mask: np.ndarray, default: int) -> int:
    indices = np.where(mask)[0]
    return int(indices[0]) if indices.size else int(default)


def _sustained_candidate(
    candidates: np.ndarray, gradient: np.ndarray, threshold: float
) -> int | None:
    for index in candidates:
        window = gradient[index : min(index + 4, len(gradient))]
        if len(window) >= 2 and float(np.mean(window > threshold)) >= 0.5:
            return int(index)
    return int(candidates[0]) if candidates.size else None


def _median_dt(time: np.ndarray) -> float:
    deltas = np.diff(time)
    if deltas.size == 0:
        return 2.0
    return float(np.clip(np.median(deltas), 1.0, 20.0))

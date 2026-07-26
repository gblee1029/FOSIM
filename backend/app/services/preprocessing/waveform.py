from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PreprocessingReport:
    sampling_rate_ms: float
    removed_duplicate_samples: int
    interpolated_columns: list[str]
    baseline_offset: float
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preprocess_waveform(waveform: pd.DataFrame) -> tuple[pd.DataFrame, PreprocessingReport]:
    clean = waveform.copy()
    original_count = len(clean)
    clean["time_ms"] = pd.to_numeric(clean["time_ms"], errors="coerce")
    clean["torque"] = pd.to_numeric(clean["torque"], errors="coerce")
    clean = clean.dropna(subset=["time_ms", "torque"])
    clean = clean.sort_values(["cycle_id", "time_ms"] if "cycle_id" in clean else ["time_ms"])
    clean = clean.drop_duplicates(["cycle_id", "time_ms"] if "cycle_id" in clean else ["time_ms"])
    removed = original_count - len(clean)
    interpolated: list[str] = []
    for column in ("speed", "angle", "current"):
        if column not in clean:
            clean[column] = np.nan
        before_missing = int(clean[column].isna().sum())
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
        clean[column] = clean[column].interpolate(limit_direction="both").fillna(0.0)
        if before_missing:
            interpolated.append(column)
    if "sample_index" not in clean:
        clean["sample_index"] = range(len(clean))
    if "cycle_id" not in clean:
        clean["cycle_id"] = "CYCLE"
    if "event_code" not in clean:
        clean["event_code"] = ""

    baseline_window = max(3, min(20, len(clean) // 10))
    baseline = float(clean["torque"].head(baseline_window).median()) if len(clean) else 0.0
    corrected = clean.copy().reset_index(drop=True)
    corrected["torque"] = (corrected["torque"] - min(0.0, baseline)).clip(lower=0.0)
    sampling_rate = _sampling_rate(corrected)
    warnings: list[str] = []
    if sampling_rate > 10:
        warnings.append("Sampling interval is coarse for seating detail analysis.")
    if removed:
        warnings.append(f"{removed} duplicate or invalid samples were removed.")
    return corrected, PreprocessingReport(
        sampling_rate_ms=sampling_rate,
        removed_duplicate_samples=removed,
        interpolated_columns=interpolated,
        baseline_offset=baseline,
        warnings=warnings,
    )


def _sampling_rate(frame: pd.DataFrame) -> float:
    if len(frame) < 2:
        return 0.0
    deltas = frame["time_ms"].astype(float).diff().dropna()
    return float(deltas.median()) if len(deltas) else 0.0

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

DEFAULT_FEATURE_NAMES = [
    "final_torque",
    "max_torque",
    "overshoot_percent",
    "total_time",
    "clamp_time",
    "seating_torque",
    "waveform_stability_score",
]

CAPABILITY_CAP = 10.0


@dataclass(frozen=True)
class FeatureDistribution:
    feature: str
    mean: float
    std: float
    min: float
    max: float
    p05: float
    p95: float
    count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_features(
    features_list: Sequence[Any],
    feature_names: Sequence[str] | None = None,
) -> dict[str, FeatureDistribution]:
    names = list(feature_names) if feature_names else list(DEFAULT_FEATURE_NAMES)
    summary: dict[str, FeatureDistribution] = {}
    for name in names:
        values = [
            float(getattr(item, name))
            for item in features_list
            if getattr(item, name, None) is not None
        ]
        if not values:
            continue
        array = np.asarray(values, dtype=float)
        summary[name] = FeatureDistribution(
            feature=name,
            mean=float(np.mean(array)),
            std=float(np.std(array, ddof=0)),
            min=float(np.min(array)),
            max=float(np.max(array)),
            p05=float(np.percentile(array, 5)),
            p95=float(np.percentile(array, 95)),
            count=int(array.size),
        )
    return summary


def process_capability(
    values: Sequence[float],
    lower_limit: float,
    upper_limit: float,
) -> float:
    """Cpk. 표본이 2개 미만이면 0.0, 산포가 0이면 CAPABILITY_CAP을 돌려준다."""
    array = np.asarray(list(values), dtype=float)
    if array.size < 2:
        return 0.0
    sigma = float(np.std(array, ddof=1))
    mean = float(np.mean(array))
    if sigma <= 1e-12:
        return CAPABILITY_CAP
    upper = (float(upper_limit) - mean) / (3.0 * sigma)
    lower = (mean - float(lower_limit)) / (3.0 * sigma)
    return float(min(min(upper, lower), CAPABILITY_CAP))

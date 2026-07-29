from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

MAD_SCALE = 0.6745


@dataclass(frozen=True)
class ExclusionEntry:
    cycle_id: str
    reason: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ExclusionResult:
    included_cycle_ids: list[str]
    excluded: list[ExclusionEntry]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "included_cycle_ids": self.included_cycle_ids,
            "included_count": len(self.included_cycle_ids),
            "excluded": [entry.to_dict() for entry in self.excluded],
            "excluded_count": len(self.excluded),
            "warnings": self.warnings,
        }


def select_included_cycles(
    cycle_ids: Sequence[str],
    diagnoses: Sequence[Any],
    final_torques: Sequence[float],
    mad_threshold: float = 3.5,
) -> ExclusionResult:
    entries: list[ExclusionEntry] = []
    excluded_ids: set[str] = set()

    for cycle_id, diagnosis in zip(cycle_ids, diagnoses):
        if getattr(diagnosis, "severity", "normal") == "warning":
            entries.append(
                ExclusionEntry(
                    cycle_id=cycle_id,
                    reason="diagnosis",
                    detail=str(getattr(diagnosis, "anomaly_type", "unknown")),
                )
            )
            excluded_ids.add(cycle_id)

    values = np.asarray(list(final_torques), dtype=float)
    if values.size >= 3:
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad > 1e-12:
            scores = MAD_SCALE * (values - median) / mad
            for cycle_id, score in zip(cycle_ids, scores):
                if cycle_id in excluded_ids:
                    continue
                if abs(float(score)) > mad_threshold:
                    entries.append(
                        ExclusionEntry(
                            cycle_id=cycle_id,
                            reason="statistical_outlier",
                            detail=f"final_torque modified z-score {float(score):.2f}",
                        )
                    )
                    excluded_ids.add(cycle_id)

    included = [cycle_id for cycle_id in cycle_ids if cycle_id not in excluded_ids]
    if not included:
        return ExclusionResult(
            included_cycle_ids=list(cycle_ids),
            excluded=[],
            warnings=[
                "모든 사이클이 배제 대상이라 배제를 적용하지 않았습니다. "
                "결과를 신뢰하기 전에 원본 데이터를 확인하십시오."
            ],
        )
    return ExclusionResult(included_cycle_ids=included, excluded=entries, warnings=[])

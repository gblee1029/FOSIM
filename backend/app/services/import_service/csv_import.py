from __future__ import annotations

from dataclasses import asdict, dataclass
from io import StringIO
from typing import Any

import pandas as pd

from app.services.preprocessing.waveform import preprocess_waveform
from app.services.simulation.simulator import FasteningSettings


REQUIRED_SETTINGS_COLUMNS = {
    "cycle_id",
    "target_speed",
    "target_torque",
    "clamp_rising_time",
    "torque_hold_time",
}
REQUIRED_WAVEFORM_COLUMNS = {"cycle_id", "sample_index", "time_ms", "torque"}


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ImportedCycle:
    cycle_id: str
    settings: FasteningSettings
    waveform: pd.DataFrame
    metadata: dict[str, Any]
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "settings": self.settings.to_dict(),
            "waveform": self.waveform.to_dict(orient="records"),
            "metadata": self.metadata,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def import_csv_pair(settings_csv: str, waveform_csv: str) -> ImportedCycle:
    return import_csv_batch(settings_csv, [waveform_csv])[0]


def import_csv_batch(settings_csv: str, waveform_csvs: list[str]) -> list[ImportedCycle]:
    if not waveform_csvs:
        raise ValueError("At least one waveform CSV is required.")

    settings_frame = _read_csv(settings_csv, "settings")
    waveform_frames = [_read_csv(content, f"waveform[{index}]") for index, content in enumerate(waveform_csvs)]
    issues = _validate_columns(settings_frame, REQUIRED_SETTINGS_COLUMNS, "settings")
    for index, frame in enumerate(waveform_frames):
        issues.extend(_validate_columns(frame, REQUIRED_WAVEFORM_COLUMNS, f"waveform[{index}]"))
    if issues:
        raise ValueError("; ".join(issue.message for issue in issues if issue.severity == "error"))

    waveform_frame = pd.concat(waveform_frames, ignore_index=True)
    imported_cycles: list[ImportedCycle] = []
    for cycle_id in _ordered_unique(waveform_frame["cycle_id"]):
        settings_row, cycle_issues = _settings_row_for_cycle(settings_frame, cycle_id)
        settings = FasteningSettings.from_mapping(settings_row)
        cycle_waveform = waveform_frame[waveform_frame["cycle_id"].astype(str) == cycle_id].copy()
        processed, report = preprocess_waveform(cycle_waveform)
        cycle_issues.extend(_validate_waveform(processed))
        metadata = {
            "product_model": settings_row.get("product_model", ""),
            "process_id": settings_row.get("process_id", ""),
            "screw_position": settings_row.get("screw_position", ""),
            "joint_type": settings_row.get("joint_type", ""),
            "settings_cycle_id": str(settings_row.get("cycle_id", "")),
            "preprocessing": report.to_dict(),
        }
        imported_cycles.append(
            ImportedCycle(
                cycle_id=cycle_id,
                settings=settings,
                waveform=processed,
                metadata=metadata,
                issues=cycle_issues,
            )
        )
    return imported_cycles


def _read_csv(content: str, label: str) -> pd.DataFrame:
    if not content.strip():
        raise ValueError(f"{label} CSV is empty.")
    try:
        return pd.read_csv(StringIO(content))
    except Exception as exc:  # pragma: no cover - pandas formats details
        raise ValueError(f"{label} CSV could not be parsed: {exc}") from exc


def _validate_columns(
    frame: pd.DataFrame,
    required_columns: set[str],
    label: str,
) -> list[ValidationIssue]:
    missing = sorted(required_columns - set(frame.columns))
    return [
        ValidationIssue(
            field=column,
            message=f"{label} CSV is missing required column '{column}'.",
        )
        for column in missing
    ]


def _settings_row_for_cycle(settings_frame: pd.DataFrame, cycle_id: str) -> tuple[dict[str, Any], list[ValidationIssue]]:
    normalized = settings_frame.copy()
    normalized["cycle_id"] = normalized["cycle_id"].astype(str)
    exact = normalized[normalized["cycle_id"] == cycle_id]
    if not exact.empty:
        return exact.iloc[0].to_dict(), []

    if len(normalized) == 1:
        row = normalized.iloc[0].to_dict()
        return row, [
            ValidationIssue(
                field="cycle_id",
                message=(
                    f"Using shared settings row '{row.get('cycle_id', '')}' "
                    f"for waveform cycle '{cycle_id}'."
                ),
                severity="warning",
            )
        ]

    raise ValueError(f"No settings row found for waveform cycle_id '{cycle_id}'.")


def _ordered_unique(values: pd.Series) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values.astype(str):
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _validate_waveform(frame: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if len(frame) < 6:
        issues.append(
            ValidationIssue(
                field="waveform",
                message="Waveform has fewer than 6 samples; segmentation may be unreliable.",
                severity="warning",
            )
        )
    if not frame["time_ms"].is_monotonic_increasing:
        issues.append(
            ValidationIssue(
                field="time_ms",
                message="time_ms was sorted during preprocessing.",
                severity="warning",
            )
        )
    return issues

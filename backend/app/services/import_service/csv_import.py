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
    settings_frame = _read_csv(settings_csv, "settings")
    waveform_frame = _read_csv(waveform_csv, "waveform")
    issues = _validate_columns(settings_frame, REQUIRED_SETTINGS_COLUMNS, "settings")
    issues.extend(_validate_columns(waveform_frame, REQUIRED_WAVEFORM_COLUMNS, "waveform"))
    if issues:
        raise ValueError("; ".join(issue.message for issue in issues if issue.severity == "error"))

    settings_row = settings_frame.iloc[0].to_dict()
    settings = FasteningSettings.from_mapping(settings_row)
    cycle_id = str(settings_row["cycle_id"])
    if set(waveform_frame["cycle_id"].astype(str).unique()) != {cycle_id}:
        issues.append(
            ValidationIssue(
                field="cycle_id",
                message="Settings cycle_id and waveform cycle_id do not match exactly.",
            )
        )
        raise ValueError(issues[-1].message)

    processed, report = preprocess_waveform(waveform_frame)
    issues.extend(_validate_waveform(processed))
    metadata = {
        "product_model": settings_row.get("product_model", ""),
        "process_id": settings_row.get("process_id", ""),
        "screw_position": settings_row.get("screw_position", ""),
        "joint_type": settings_row.get("joint_type", ""),
        "preprocessing": report.to_dict(),
    }
    return ImportedCycle(
        cycle_id=cycle_id,
        settings=settings,
        waveform=processed,
        metadata=metadata,
        issues=issues,
    )


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

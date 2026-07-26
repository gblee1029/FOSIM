from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Diagnosis:
    anomaly_type: str
    severity: str
    confidence: float
    evidence_features: list[str]
    related_parameters: list[str]
    recommended_checks: list[str]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def diagnose(features: Any) -> Diagnosis:
    if features.overshoot_percent > 5.0:
        return Diagnosis(
            anomaly_type="Torque Overshoot",
            severity="warning",
            confidence=min(0.94, 0.7 + features.overshoot_percent / 60.0),
            evidence_features=[
                f"overshoot_percent={features.overshoot_percent:.2f}",
                f"clamp_gradient={features.clamp_gradient:.5f}",
                f"peak_torque={features.peak_torque:.3f}",
            ],
            related_parameters=["clamp_rising_time", "target_speed", "speed_adjust_time"],
            recommended_checks=[
                "Check seating impact and clamp rising speed.",
                "Verify torque upper limit before changing Target Torque.",
            ],
            description="Peak torque is above target torque by more than the MVP threshold.",
        )
    if features.undershoot_percent > 5.0:
        return Diagnosis(
            anomaly_type="Torque Undershoot",
            severity="warning",
            confidence=min(0.9, 0.68 + features.undershoot_percent / 70.0),
            evidence_features=[
                f"undershoot_percent={features.undershoot_percent:.2f}",
                f"final_torque={features.final_torque:.3f}",
            ],
            related_parameters=["torque_hold_time", "clamp_rising_time", "target_speed"],
            recommended_checks=[
                "Check max time and max angle before increasing target torque.",
                "Confirm seating was not detected too early.",
            ],
            description="Final torque is below target torque by more than the MVP threshold.",
        )
    if features.seating_confidence < 0.65:
        return Diagnosis(
            anomaly_type="Early or Late Seating Suspected",
            severity="caution",
            confidence=0.62,
            evidence_features=[f"seating_confidence={features.seating_confidence:.2f}"],
            related_parameters=["seating_sensitivity", "target_speed"],
            recommended_checks=[
                "Review seating marker manually.",
                "Compare A1/A2 angle against normal cycles.",
            ],
            description="Rule-based segmentation could not isolate seating sharply.",
        )
    if features.hold_std > max(0.04, features.hold_mean_torque * 0.05):
        return Diagnosis(
            anomaly_type="Hold Instability",
            severity="caution",
            confidence=0.72,
            evidence_features=[
                f"hold_std={features.hold_std:.4f}",
                f"hold_mean_torque={features.hold_mean_torque:.3f}",
            ],
            related_parameters=["torque_hold_time", "clamp_rising_time"],
            recommended_checks=["Inspect joint friction and driver stop behavior."],
            description="Hold torque variation is above the MVP stability threshold.",
        )
    return Diagnosis(
        anomaly_type="Normal",
        severity="normal",
        confidence=0.82,
        evidence_features=[
            f"overshoot_percent={features.overshoot_percent:.2f}",
            f"waveform_stability_score={features.waveform_stability_score:.2f}",
        ],
        related_parameters=[],
        recommended_checks=["Run repeated cycles before applying production limits."],
        description="No MVP rule threshold was exceeded.",
    )

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.services.simulation.simulator import FasteningSettings, SimulationResult, simulate_waveform


@dataclass(frozen=True)
class OptimizationObjectives:
    target_torque_min: float
    target_torque_max: float
    max_overshoot_percent: float
    max_fastening_time: float
    min_stability_score: float = 0.65
    allow_target_torque_change: bool = False
    max_candidates: int = 500

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "OptimizationObjectives":
        return cls(
            target_torque_min=float(value["target_torque_min"]),
            target_torque_max=float(value["target_torque_max"]),
            max_overshoot_percent=float(value["max_overshoot_percent"]),
            max_fastening_time=float(value["max_fastening_time"]),
            min_stability_score=float(value.get("min_stability_score", 0.65)),
            allow_target_torque_change=bool(value.get("allow_target_torque_change", False)),
            max_candidates=int(value.get("max_candidates", 500)),
        )


@dataclass(frozen=True)
class CandidateEvaluation:
    label: str
    settings: FasteningSettings
    score: float
    score_breakdown: dict[str, float]
    simulation: SimulationResult
    reason: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "settings": self.settings.to_dict(),
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "simulation": self.simulation.to_dict(),
            "reason": self.reason,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class OptimizationResult:
    evaluated_count: int
    rejected_count: int
    recommended: list[CandidateEvaluation]
    all_candidates: list[CandidateEvaluation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_count": self.evaluated_count,
            "rejected_count": self.rejected_count,
            "recommended": [candidate.to_dict() for candidate in self.recommended],
            "all_candidates": [candidate.to_dict() for candidate in self.all_candidates],
        }


def optimize_candidates(
    waveform: pd.DataFrame,
    current_settings: FasteningSettings,
    objectives: OptimizationObjectives,
    parameter_ranges: dict[str, dict[str, float]] | None = None,
) -> OptimizationResult:
    candidates = _generate_candidates(current_settings, objectives, parameter_ranges)
    evaluated: list[CandidateEvaluation] = []
    rejected = 0
    for candidate in candidates[: objectives.max_candidates]:
        simulation = simulate_waveform(waveform, current_settings, candidate)
        violations = _constraint_violations(simulation, objectives)
        if violations:
            rejected += 1
            continue
        score, breakdown = _score_candidate(simulation, current_settings, objectives)
        evaluated.append(
            CandidateEvaluation(
                label="unassigned",
                settings=candidate,
                score=score,
                score_breakdown=breakdown,
                simulation=simulation,
                reason="Candidate satisfies MVP constraints.",
                warnings=simulation.warnings,
            )
        )

    if not evaluated:
        for candidate in candidates[: min(20, len(candidates))]:
            simulation = simulate_waveform(waveform, current_settings, candidate)
            score, breakdown = _score_candidate(simulation, current_settings, objectives)
            evaluated.append(
                CandidateEvaluation(
                    label="unassigned",
                    settings=candidate,
                    score=score * 0.6,
                    score_breakdown=breakdown,
                    simulation=simulation,
                    reason="Fallback candidate; review constraints before use.",
                    warnings=simulation.warnings + _constraint_violations(simulation, objectives),
                )
            )

    recommended = _select_recommended(evaluated, current_settings)
    return OptimizationResult(
        evaluated_count=len(evaluated),
        rejected_count=rejected,
        recommended=recommended,
        all_candidates=sorted(evaluated, key=lambda item: item.score, reverse=True)[:20],
    )


def _generate_candidates(
    current: FasteningSettings,
    objectives: OptimizationObjectives,
    parameter_ranges: dict[str, dict[str, float]] | None,
) -> list[FasteningSettings]:
    if parameter_ranges:
        speeds = _range_values(parameter_ranges.get("target_speed"), [current.target_speed])
        clamps = _range_values(parameter_ranges.get("clamp_rising_time"), [current.clamp_rising_time])
        holds = _range_values(parameter_ranges.get("torque_hold_time"), [current.torque_hold_time])
    else:
        speeds = sorted({round(current.target_speed * factor, 2) for factor in (0.9, 0.95, 1.0, 1.05)})
        clamps = sorted({max(20.0, current.clamp_rising_time + delta) for delta in (-20, 0, 20, 40, 60)})
        holds = sorted({max(0.0, current.torque_hold_time + delta) for delta in (0, 10, 20, 30)})

    if objectives.allow_target_torque_change:
        targets = sorted(
            {
                round(value, 4)
                for value in (
                    objectives.target_torque_min,
                    current.target_torque,
                    objectives.target_torque_max,
                )
            }
        )
    else:
        targets = [current.target_torque]

    candidates: list[FasteningSettings] = []
    for speed in speeds:
        for clamp in clamps:
            for hold in holds:
                for target in targets:
                    if target < objectives.target_torque_min or target > objectives.target_torque_max:
                        continue
                    candidates.append(
                        FasteningSettings(
                            target_speed=float(speed),
                            target_torque=float(target),
                            clamp_rising_time=float(clamp),
                            torque_hold_time=float(hold),
                            seating_sensitivity=current.seating_sensitivity,
                            speed_adjust_time=current.speed_adjust_time,
                        )
                    )
    return candidates


def _range_values(config: dict[str, float] | None, fallback: list[float]) -> list[float]:
    if not config:
        return fallback
    start = float(config["min"])
    stop = float(config["max"])
    step = float(config.get("step", max((stop - start) / 4.0, 1.0)))
    if step <= 0:
        return fallback
    values = []
    current = start
    while current <= stop + 1e-9:
        values.append(round(current, 4))
        current += step
    return values


def _constraint_violations(
    simulation: SimulationResult, objectives: OptimizationObjectives
) -> list[str]:
    features = simulation.predicted_features
    violations: list[str] = []
    if not (objectives.target_torque_min <= features.final_torque <= objectives.target_torque_max):
        violations.append("Predicted final torque is outside the objective range.")
    if features.overshoot_percent > objectives.max_overshoot_percent:
        violations.append("Predicted overshoot exceeds the objective limit.")
    if features.total_time > objectives.max_fastening_time:
        violations.append("Predicted fastening time exceeds the objective limit.")
    if features.waveform_stability_score < objectives.min_stability_score:
        violations.append("Predicted stability is below the objective limit.")
    if simulation.confidence.score < 0.45:
        violations.append("Prediction confidence is below the MVP minimum.")
    return violations


def _score_candidate(
    simulation: SimulationResult,
    current: FasteningSettings,
    objectives: OptimizationObjectives,
) -> tuple[float, dict[str, float]]:
    features = simulation.predicted_features
    target_mid = (objectives.target_torque_min + objectives.target_torque_max) / 2.0
    tolerance = max((objectives.target_torque_max - objectives.target_torque_min) / 2.0, 0.001)
    torque_accuracy = 1.0 - min(1.0, abs(features.final_torque - target_mid) / tolerance)
    overshoot_score = 1.0 - min(1.0, features.overshoot_percent / max(objectives.max_overshoot_percent, 0.1))
    time_score = 1.0 - min(1.0, features.total_time / max(objectives.max_fastening_time, 1.0))
    stability_score = features.waveform_stability_score
    change_score = 1.0 - min(1.0, _change_distance(current, simulation.candidate_settings))
    constraint_score = 1.0 if not _constraint_violations(simulation, objectives) else 0.0
    breakdown = {
        "constraint": constraint_score * 35.0,
        "torque_accuracy": torque_accuracy * 20.0,
        "overshoot": overshoot_score * 15.0,
        "clamp_stability": stability_score * 10.0,
        "hold_stability": stability_score * 10.0,
        "fastening_time": time_score * 5.0,
        "setting_change": change_score * 5.0,
    }
    score = float(sum(breakdown.values()))
    return score, breakdown


def _change_distance(current: FasteningSettings, candidate: FasteningSettings) -> float:
    parts = [
        abs(candidate.target_speed - current.target_speed) / max(current.target_speed, 1.0),
        abs(candidate.clamp_rising_time - current.clamp_rising_time) / max(current.clamp_rising_time, 1.0),
        abs(candidate.torque_hold_time - current.torque_hold_time) / max(current.torque_hold_time, 1.0),
        abs(candidate.target_torque - current.target_torque) / max(current.target_torque, 0.001),
    ]
    return float(np.mean(parts))


def _select_recommended(
    evaluated: list[CandidateEvaluation],
    current_settings: FasteningSettings,
) -> list[CandidateEvaluation]:
    if not evaluated:
        return []
    quality = min(
        evaluated,
        key=lambda item: (
            item.simulation.predicted_features.overshoot_percent,
            -item.simulation.predicted_features.waveform_stability_score,
            -item.score,
        ),
    )
    cycle = min(
        evaluated,
        key=lambda item: (
            item.simulation.predicted_features.total_time,
            -item.score,
        ),
    )
    minimum = min(
        evaluated,
        key=lambda item: (
            _change_distance(current_settings, item.settings),
            -item.score,
        ),
    )
    selected = [
        _with_label(quality, "quality_stable", "Best balance for reducing overshoot and stabilizing clamp/hold."),
        _with_label(cycle, "cycle_time", "Fastest predicted cycle while satisfying MVP constraints."),
        _with_label(minimum, "minimum_change", "Smallest setting movement with acceptable predicted quality."),
    ]
    by_label: dict[str, CandidateEvaluation] = {}
    for item in selected:
        by_label[item.label] = item
    return list(by_label.values())


def _with_label(candidate: CandidateEvaluation, label: str, reason: str) -> CandidateEvaluation:
    return CandidateEvaluation(
        label=label,
        settings=candidate.settings,
        score=candidate.score,
        score_breakdown=candidate.score_breakdown,
        simulation=candidate.simulation,
        reason=reason,
        warnings=candidate.warnings,
    )

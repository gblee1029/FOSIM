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


WORST_CASE_GATE_LIMIT = 20


@dataclass(frozen=True)
class CycleEvaluation:
    cycle_id: str
    simulation: SimulationResult
    violations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "simulation": self.simulation.to_dict(),
            "violations": self.violations,
        }


def confidence_grade(cycle_count: int) -> str:
    if cycle_count < 5:
        return "reference"
    if cycle_count < WORST_CASE_GATE_LIMIT:
        return "moderate"
    return "statistical"


def _gate_mode(cycle_count: int) -> str:
    return "worst" if cycle_count < WORST_CASE_GATE_LIMIT else "p95"


def _group_violations(
    evaluations: list[CycleEvaluation],
    objectives: OptimizationObjectives,
    gate_mode: str,
) -> list[str]:
    if gate_mode == "worst":
        violations: list[str] = []
        for evaluation in evaluations:
            violations.extend(evaluation.violations)
        return sorted(set(violations))

    features = [item.simulation.predicted_features for item in evaluations]
    final_torques = np.asarray([f.final_torque for f in features], dtype=float)
    overshoots = np.asarray([f.overshoot_percent for f in features], dtype=float)
    total_times = np.asarray([f.total_time for f in features], dtype=float)
    stabilities = np.asarray([f.waveform_stability_score for f in features], dtype=float)
    confidences = np.asarray([item.simulation.confidence.score for item in evaluations], dtype=float)

    violations = []
    if float(np.percentile(final_torques, 5)) < objectives.target_torque_min or float(
        np.percentile(final_torques, 95)
    ) > objectives.target_torque_max:
        violations.append("Predicted final torque is outside the objective range.")
    if float(np.percentile(overshoots, 95)) > objectives.max_overshoot_percent:
        violations.append("Predicted overshoot exceeds the objective limit.")
    if float(np.percentile(total_times, 95)) > objectives.max_fastening_time:
        violations.append("Predicted fastening time exceeds the objective limit.")
    if float(np.percentile(stabilities, 5)) < objectives.min_stability_score:
        violations.append("Predicted stability is below the objective limit.")
    if float(np.percentile(confidences, 5)) < 0.45:
        violations.append("Prediction confidence is below the MVP minimum.")
    return violations


@dataclass(frozen=True)
class CandidateEvaluation:
    label: str
    settings: FasteningSettings
    score: float
    score_breakdown: dict[str, float]
    simulation: SimulationResult
    reason: str
    warnings: list[str]
    per_cycle: list[CycleEvaluation]
    gate_mode: str
    confidence_grade: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "settings": self.settings.to_dict(),
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "simulation": self.simulation.to_dict(),
            "reason": self.reason,
            "warnings": self.warnings,
            "per_cycle": [item.to_dict() for item in self.per_cycle],
            "cycle_count": len(self.per_cycle),
            "gate_mode": self.gate_mode,
            "confidence_grade": self.confidence_grade,
        }


@dataclass(frozen=True)
class OptimizationResult:
    evaluated_count: int
    rejected_count: int
    recommended: list[CandidateEvaluation]
    all_candidates: list[CandidateEvaluation]
    rejection_details: list[dict[str, Any]]
    cycle_count: int
    gate_mode: str
    confidence_grade: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_count": self.evaluated_count,
            "rejected_count": self.rejected_count,
            "recommended": [candidate.to_dict() for candidate in self.recommended],
            "all_candidates": [candidate.to_dict() for candidate in self.all_candidates],
            "rejection_details": self.rejection_details,
            "cycle_count": self.cycle_count,
            "gate_mode": self.gate_mode,
            "confidence_grade": self.confidence_grade,
        }


def optimize_candidates(
    waveforms: list[pd.DataFrame],
    current_settings: FasteningSettings,
    objectives: OptimizationObjectives,
    parameter_ranges: dict[str, dict[str, float]] | None = None,
) -> OptimizationResult:
    if not waveforms:
        raise ValueError("optimize_candidates requires at least one waveform.")

    cycle_ids = [_waveform_cycle_id(frame, index) for index, frame in enumerate(waveforms)]
    cycle_count = len(waveforms)
    gate_mode = _gate_mode(cycle_count)
    grade = confidence_grade(cycle_count)

    candidates = _generate_candidates(current_settings, objectives, parameter_ranges)
    evaluated: list[CandidateEvaluation] = []
    all_evaluations: list[tuple[FasteningSettings, list[CycleEvaluation], list[str]]] = []
    rejection_details: list[dict[str, Any]] = []
    rejected = 0

    for candidate in candidates[: objectives.max_candidates]:
        per_cycle = [
            CycleEvaluation(
                cycle_id=cycle_id,
                simulation=(simulation := simulate_waveform(frame, current_settings, candidate)),
                violations=_constraint_violations(simulation, objectives),
            )
            for cycle_id, frame in zip(cycle_ids, waveforms)
        ]
        group_violations = _group_violations(per_cycle, objectives, gate_mode)
        all_evaluations.append((candidate, per_cycle, group_violations))
        if group_violations:
            rejected += 1
            for item in per_cycle:
                for violation in item.violations:
                    rejection_details.append(
                        {
                            "settings": candidate.to_dict(),
                            "cycle_id": item.cycle_id,
                            "violation": violation,
                        }
                    )
            continue
        evaluated.append(
            _build_evaluation(
                candidate,
                per_cycle,
                current_settings,
                objectives,
                gate_mode,
                grade,
                reason="Candidate satisfies MVP constraints across the cycle group.",
            )
        )

    if not evaluated:
        for candidate, per_cycle, group_violations in all_evaluations[: min(20, len(all_evaluations))]:
            fallback = _build_evaluation(
                candidate,
                per_cycle,
                current_settings,
                objectives,
                gate_mode,
                grade,
                reason="Fallback candidate; review constraints before use.",
                extra_warnings=group_violations,
            )
            evaluated.append(
                CandidateEvaluation(
                    label=fallback.label,
                    settings=fallback.settings,
                    score=fallback.score * 0.6,
                    score_breakdown=fallback.score_breakdown,
                    simulation=fallback.simulation,
                    reason=fallback.reason,
                    warnings=fallback.warnings,
                    per_cycle=fallback.per_cycle,
                    gate_mode=fallback.gate_mode,
                    confidence_grade=fallback.confidence_grade,
                )
            )

    recommended = _select_recommended(evaluated, current_settings)
    return OptimizationResult(
        evaluated_count=len(evaluated),
        rejected_count=rejected,
        recommended=recommended,
        all_candidates=sorted(evaluated, key=lambda item: item.score, reverse=True)[:20],
        rejection_details=rejection_details[:100],
        cycle_count=cycle_count,
        gate_mode=gate_mode,
        confidence_grade=grade,
    )


def _waveform_cycle_id(frame: pd.DataFrame, index: int) -> str:
    if "cycle_id" in frame.columns and len(frame) > 0:
        return str(frame["cycle_id"].iloc[0])
    return f"cycle-{index}"


def _worst_cycle(per_cycle: list[CycleEvaluation]) -> CycleEvaluation:
    return max(
        per_cycle,
        key=lambda item: item.simulation.predicted_features.overshoot_percent,
    )


def _build_evaluation(
    candidate: FasteningSettings,
    per_cycle: list[CycleEvaluation],
    current_settings: FasteningSettings,
    objectives: OptimizationObjectives,
    gate_mode: str,
    grade: str,
    reason: str,
    extra_warnings: list[str] | None = None,
) -> CandidateEvaluation:
    worst = _worst_cycle(per_cycle)
    score, breakdown = _score_candidate(per_cycle, current_settings, objectives)
    warnings = list(worst.simulation.warnings) + list(extra_warnings or [])
    return CandidateEvaluation(
        label="unassigned",
        settings=candidate,
        score=score,
        score_breakdown=breakdown,
        simulation=worst.simulation,
        reason=reason,
        warnings=warnings,
        per_cycle=per_cycle,
        gate_mode=gate_mode,
        confidence_grade=grade,
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
    per_cycle: list[CycleEvaluation],
    current: FasteningSettings,
    objectives: OptimizationObjectives,
) -> tuple[float, dict[str, float]]:
    features = [item.simulation.predicted_features for item in per_cycle]
    final_torques = np.asarray([f.final_torque for f in features], dtype=float)
    peak_torques = np.asarray([f.max_torque for f in features], dtype=float)
    total_times = np.asarray([f.total_time for f in features], dtype=float)
    worst_overshoot = float(max(f.overshoot_percent for f in features))
    worst_stability = float(min(f.waveform_stability_score for f in features))

    target_mid = (objectives.target_torque_min + objectives.target_torque_max) / 2.0
    tolerance = max((objectives.target_torque_max - objectives.target_torque_min) / 2.0, 0.001)

    torque_accuracy = 1.0 - min(1.0, abs(float(np.mean(final_torques)) - target_mid) / tolerance)
    overshoot_score = 1.0 - min(
        1.0, worst_overshoot / max(objectives.max_overshoot_percent, 0.1)
    )
    time_score = 1.0 - min(
        1.0, float(np.mean(total_times)) / max(objectives.max_fastening_time, 1.0)
    )
    change_score = 1.0 - min(
        1.0, _change_distance(current, per_cycle[0].simulation.candidate_settings)
    )
    constraint_score = 1.0 if not any(item.violations for item in per_cycle) else 0.0

    # 관측된 사이클 간 변동이 시뮬레이터를 통과해 만드는 결과 산포.
    # 이 후보가 공정 산포를 줄인다는 예측이 아니다.
    #
    # 예측 최종 토크가 아니라 예측 피크 토크의 산포를 쓴다. 시뮬레이터의
    # predicted_final은 후보 설정만으로 결정되어 사이클마다 값이 같고, 따라서
    # 산포가 항상 0이 되어 모든 후보에 같은 점수를 준다. 피크 토크는 각 사이클의
    # 관측된 오버슈트를 통해 계산되므로 사이클 간 변동을 실제로 반영한다.
    if peak_torques.size < 2:
        reproducibility = 1.0
    else:
        spread = float(np.std(peak_torques, ddof=1))
        reproducibility = 1.0 - min(1.0, spread / tolerance)

    breakdown = {
        "constraint": constraint_score * 30.0,
        "torque_accuracy": torque_accuracy * 15.0,
        "reproducibility": reproducibility * 20.0,
        "overshoot": overshoot_score * 15.0,
        "stability": worst_stability * 15.0,
        "fastening_time": time_score * 3.0,
        "setting_change": change_score * 2.0,
    }
    return float(sum(breakdown.values())), breakdown


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
        per_cycle=candidate.per_cycle,
        gate_mode=candidate.gate_mode,
        confidence_grade=candidate.confidence_grade,
    )

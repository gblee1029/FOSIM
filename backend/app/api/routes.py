from __future__ import annotations

import json
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_session
from app.db.models import AnalysisRecord, CycleRecord, OptimizationRecord, SettingsRecord, SimulationRecord
from app.services.diagnosis.rules import diagnose
from app.services.feature_extraction.features import extract_features
from app.services.group_analysis.exclusion import select_included_cycles
from app.services.group_analysis.grouping import group_cycles_by_settings
from app.services.group_analysis.statistics import (
    compute_envelope,
    process_capability,
    summarize_features,
)
from app.services.import_service.csv_import import ImportedCycle, import_csv_batch
from app.services.import_service.sample_data import synthetic_settings, synthetic_waveform
from app.services.optimization.optimizer import (
    OptimizationObjectives,
    confidence_grade,
    optimize_candidates,
)
from app.services.segmentation.segments import detect_segments
from app.services.simulation.simulator import FasteningSettings, simulate_waveform


router = APIRouter()


class CsvImportRequest(BaseModel):
    settings_csv: str
    waveform_csv: str | None = None
    waveform_csvs: list[str] | None = None

    def waveform_contents(self) -> list[str]:
        contents: list[str] = []
        if self.waveform_csv:
            contents.append(self.waveform_csv)
        if self.waveform_csvs:
            contents.extend(self.waveform_csvs)
        return contents


class SimulationRequest(BaseModel):
    waveform: list[dict[str, Any]]
    current_settings: dict[str, Any]
    candidate_settings: dict[str, Any]


class OptimizationRequest(BaseModel):
    waveform: list[dict[str, Any]] | None = None
    waveforms: list[list[dict[str, Any]]] | None = None
    current_settings: dict[str, Any]
    objectives: dict[str, Any]
    parameter_ranges: dict[str, dict[str, float]] | None = None

    def waveform_frames(self) -> list[pd.DataFrame]:
        frames: list[pd.DataFrame] = []
        if self.waveform:
            frames.append(pd.DataFrame(self.waveform))
        if self.waveforms:
            frames.extend(pd.DataFrame(item) for item in self.waveforms)
        if not frames:
            raise ValueError("At least one waveform is required.")
        return frames


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sh2-fastening-optimizer"}


@router.get("/sample/cycle")
def sample_cycle() -> dict[str, Any]:
    settings_csv = synthetic_settings().to_csv(index=False)
    waveform_csv = synthetic_waveform().to_csv(index=False)
    return _analyze_import(settings_csv, [waveform_csv])


@router.post("/import/csv")
def import_csv(request: CsvImportRequest) -> dict[str, Any]:
    try:
        return _analyze_import(request.settings_csv, request.waveform_contents())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/simulations")
def run_simulation(request: SimulationRequest) -> dict[str, Any]:
    waveform = pd.DataFrame(request.waveform)
    current = FasteningSettings.from_mapping(request.current_settings)
    candidate = FasteningSettings.from_mapping(request.candidate_settings)
    result = simulate_waveform(waveform, current, candidate).to_dict()
    _store_simulation(result)
    return result


@router.post("/optimizations")
def run_optimization(request: OptimizationRequest) -> dict[str, Any]:
    try:
        frames = request.waveform_frames()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    settings = FasteningSettings.from_mapping(request.current_settings)
    objectives = OptimizationObjectives.from_mapping(request.objectives)
    result = optimize_candidates(
        frames,
        settings,
        objectives,
        parameter_ranges=request.parameter_ranges,
    ).to_dict()
    _store_optimization(str(frames[0]["cycle_id"].iloc[0]), request.objectives, result)
    return result


def _analyze_import(settings_csv: str, waveform_csvs: list[str]) -> dict[str, Any]:
    imported_cycles = import_csv_batch(settings_csv, waveform_csvs)
    analyzed_cycles = [_analyze_cycle(imported) for imported in imported_cycles]
    response = {
        **analyzed_cycles[0],
        "cycles": analyzed_cycles,
        "active_cycle_id": analyzed_cycles[0]["cycle"]["cycle_id"],
        "group_summary": _build_group_summary(imported_cycles),
    }
    _store_import(response)
    return response


def _build_group_summary(imported_cycles: list[ImportedCycle]) -> dict[str, Any]:
    groups = group_cycles_by_settings(imported_cycles)
    active = groups[0]
    members = [cycle for cycle in imported_cycles if cycle.cycle_id in set(active.cycle_ids)]

    features_list = []
    diagnoses = []
    for cycle in members:
        segments = detect_segments(cycle.waveform, cycle.settings)
        features = extract_features(cycle.waveform, segments, cycle.settings)
        features_list.append(features)
        diagnoses.append(diagnose(features))

    final_torques = [float(features.final_torque) for features in features_list]
    target = float(active.settings.target_torque)
    exclusion = select_included_cycles(
        [cycle.cycle_id for cycle in members], diagnoses, final_torques
    )
    distributions = summarize_features(features_list)
    envelope = compute_envelope([cycle.waveform for cycle in members])

    return {
        "groups": [group.to_dict() for group in groups],
        "is_single_group": len(groups) == 1,
        "active_group_index": 0,
        "distributions": {
            name: dist.to_dict() for name, dist in distributions.items()
        },
        "capability": {
            "final_torque_cpk": process_capability(
                final_torques, target * 0.97, target * 1.03
            )
        },
        "envelope": envelope.to_dict(),
        "exclusion": exclusion.to_dict(),
        "confidence_grade": confidence_grade(len(members)),
    }


def _analyze_cycle(imported: ImportedCycle) -> dict[str, Any]:
    segments = detect_segments(imported.waveform, imported.settings)
    features = extract_features(imported.waveform, segments, imported.settings)
    diagnosis = diagnose(features)
    return {
        "cycle": imported.to_dict(),
        "analysis": {
            "segments": segments.to_dict(),
            "features": features.to_dict(),
            "diagnosis": diagnosis.to_dict(),
        },
    }


def _store_import(payload: dict[str, Any]) -> None:
    entries = payload.get("cycles") or [{"cycle": payload["cycle"], "analysis": payload["analysis"]}]
    for entry in entries:
        _store_import_entry(entry)


def _store_import_entry(entry: dict[str, Any]) -> None:
    cycle = entry["cycle"]
    settings = cycle["settings"]
    analysis = entry["analysis"]
    session = get_session()
    try:
        session.add(
            CycleRecord(
                cycle_id=cycle["cycle_id"],
                product_model=cycle["metadata"].get("product_model", ""),
                process_id=cycle["metadata"].get("process_id", ""),
                screw_position=cycle["metadata"].get("screw_position", ""),
                joint_type=cycle["metadata"].get("joint_type", ""),
            )
        )
        session.add(
            SettingsRecord(
                cycle_id=cycle["cycle_id"],
                target_speed=settings["target_speed"],
                target_torque=settings["target_torque"],
                clamp_rising_time=settings["clamp_rising_time"],
                torque_hold_time=settings["torque_hold_time"],
                raw_json=json.dumps(settings),
            )
        )
        session.add(
            AnalysisRecord(
                cycle_id=cycle["cycle_id"],
                segments_json=json.dumps(analysis["segments"]),
                features_json=json.dumps(analysis["features"]),
                diagnosis_json=json.dumps(analysis["diagnosis"]),
            )
        )
        session.commit()
    finally:
        session.close()


def _store_simulation(payload: dict[str, Any]) -> None:
    session = get_session()
    try:
        session.add(
            SimulationRecord(
                cycle_id=payload.get("source_cycle_id", ""),
                current_settings_json=json.dumps(payload["current_settings"]),
                candidate_settings_json=json.dumps(payload["candidate_settings"]),
                predicted_features_json=json.dumps(payload["predicted_features"]),
                confidence_json=json.dumps(payload["confidence"]),
                warnings_json=json.dumps(payload["warnings"]),
            )
        )
        session.commit()
    finally:
        session.close()


def _store_optimization(cycle_id: str, objectives: dict[str, Any], payload: dict[str, Any]) -> None:
    session = get_session()
    try:
        session.add(
            OptimizationRecord(
                cycle_id=cycle_id,
                objectives_json=json.dumps(objectives),
                candidate_count=int(payload["evaluated_count"]),
                result_json=json.dumps(payload),
            )
        )
        session.commit()
    finally:
        session.close()

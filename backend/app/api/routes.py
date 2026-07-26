from __future__ import annotations

import json
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.database import get_session
from app.db.models import AnalysisRecord, CycleRecord, OptimizationRecord, SettingsRecord, SimulationRecord
from app.services.diagnosis.rules import diagnose
from app.services.feature_extraction.features import extract_features
from app.services.import_service.csv_import import import_csv_pair
from app.services.import_service.sample_data import synthetic_settings, synthetic_waveform
from app.services.optimization.optimizer import OptimizationObjectives, optimize_candidates
from app.services.segmentation.segments import detect_segments
from app.services.simulation.simulator import FasteningSettings, simulate_waveform


router = APIRouter()


class CsvImportRequest(BaseModel):
    settings_csv: str
    waveform_csv: str


class SimulationRequest(BaseModel):
    waveform: list[dict[str, Any]]
    current_settings: dict[str, Any]
    candidate_settings: dict[str, Any]


class OptimizationRequest(BaseModel):
    waveform: list[dict[str, Any]]
    current_settings: dict[str, Any]
    objectives: dict[str, Any]
    parameter_ranges: dict[str, dict[str, float]] | None = None


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sh2-fastening-optimizer"}


@router.get("/sample/cycle")
def sample_cycle() -> dict[str, Any]:
    settings_csv = synthetic_settings().to_csv(index=False)
    waveform_csv = synthetic_waveform().to_csv(index=False)
    return _analyze_import(settings_csv, waveform_csv)


@router.post("/import/csv")
def import_csv(request: CsvImportRequest) -> dict[str, Any]:
    try:
        return _analyze_import(request.settings_csv, request.waveform_csv)
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
    waveform = pd.DataFrame(request.waveform)
    settings = FasteningSettings.from_mapping(request.current_settings)
    objectives = OptimizationObjectives.from_mapping(request.objectives)
    result = optimize_candidates(
        waveform,
        settings,
        objectives,
        parameter_ranges=request.parameter_ranges,
    ).to_dict()
    _store_optimization(str(waveform["cycle_id"].iloc[0]), request.objectives, result)
    return result


def _analyze_import(settings_csv: str, waveform_csv: str) -> dict[str, Any]:
    imported = import_csv_pair(settings_csv, waveform_csv)
    segments = detect_segments(imported.waveform, imported.settings)
    features = extract_features(imported.waveform, segments, imported.settings)
    diagnosis = diagnose(features)
    response = {
        "cycle": imported.to_dict(),
        "analysis": {
            "segments": segments.to_dict(),
            "features": features.to_dict(),
            "diagnosis": diagnosis.to_dict(),
        },
    }
    _store_import(response)
    return response


def _store_import(payload: dict[str, Any]) -> None:
    cycle = payload["cycle"]
    settings = cycle["settings"]
    analysis = payload["analysis"]
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

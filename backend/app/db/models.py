from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CycleRecord(Base):
    __tablename__ = "cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(String(120), index=True)
    product_model: Mapped[str] = mapped_column(String(120), default="")
    process_id: Mapped[str] = mapped_column(String(120), default="")
    screw_position: Mapped[str] = mapped_column(String(120), default="")
    joint_type: Mapped[str] = mapped_column(String(60), default="")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SettingsRecord(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(String(120), index=True)
    target_speed: Mapped[float] = mapped_column(Float)
    target_torque: Mapped[float] = mapped_column(Float)
    clamp_rising_time: Mapped[float] = mapped_column(Float)
    torque_hold_time: Mapped[float] = mapped_column(Float)
    raw_json: Mapped[str] = mapped_column(Text)


class AnalysisRecord(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(String(120), index=True)
    segments_json: Mapped[str] = mapped_column(Text)
    features_json: Mapped[str] = mapped_column(Text)
    diagnosis_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SimulationRecord(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(String(120), index=True)
    current_settings_json: Mapped[str] = mapped_column(Text)
    candidate_settings_json: Mapped[str] = mapped_column(Text)
    predicted_features_json: Mapped[str] = mapped_column(Text)
    confidence_json: Mapped[str] = mapped_column(Text)
    warnings_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OptimizationRecord(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(String(120), index=True)
    objectives_json: Mapped[str] = mapped_column(Text)
    candidate_count: Mapped[int] = mapped_column(Integer)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

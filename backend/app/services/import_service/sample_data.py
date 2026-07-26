from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def synthetic_settings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cycle_id": "CYCLE-NORMAL-001",
                "product_model": "MODEL-A",
                "process_id": "P10",
                "screw_position": "S01",
                "joint_type": "HARD",
                "target_speed": 820,
                "target_torque": 1.20,
                "clamp_rising_time": 100,
                "torque_hold_time": 30,
                "seating_sensitivity": 50,
                "speed_adjust_time": 25,
            }
        ]
    )


def synthetic_waveform(cycle_id: str = "CYCLE-NORMAL-001", mode: str = "normal") -> pd.DataFrame:
    rows = []
    target = 1.2
    for index in range(0, 261):
        t = float(index * 2)
        if t < 75:
            torque = 0.025 + 0.00022 * t
            speed = 820 * (1 - math.exp(-t / 22))
            angle = t * 0.09
        elif t < 145:
            torque = 0.07 + (t - 75) * 0.0032
            speed = 800 - (t - 75) * 1.1
            angle = 6.8 + (t - 75) * 0.085
        elif t < 285:
            torque = 0.30 + (target - 0.30) * (1 - math.exp(-(t - 145) / 58))
            speed = max(80, 650 - (t - 145) * 1.9)
            angle = 12.8 + (t - 145) * 0.052
        elif t < 335:
            overshoot = 0.025 if mode == "normal" else 0.10
            torque = target * (1 + overshoot) + 0.012 * math.sin((t - 285) / 5)
            speed = max(0.0, 150 - (t - 285) * 3.0)
            angle = 20.1 + (t - 285) * 0.01
        else:
            torque = max(0.18, target * 0.93 * math.exp(-(t - 335) / 95))
            speed = 0.0
            angle = 20.6
        if mode == "undershoot":
            torque *= 0.88
        rows.append(
            {
                "cycle_id": cycle_id,
                "sample_index": index,
                "time_ms": t,
                "torque": round(torque, 5),
                "speed": round(speed, 3),
                "angle": round(angle, 4),
                "current": round(0.2 + torque * 0.82, 4),
                "event_code": "",
            }
        )
    return pd.DataFrame(rows)


def write_sample_files(root: Path) -> None:
    settings_dir = root / "sample-data" / "settings"
    waveform_dir = root / "sample-data" / "waveforms"
    expected_dir = root / "sample-data" / "expected-results"
    settings_dir.mkdir(parents=True, exist_ok=True)
    waveform_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)
    synthetic_settings().to_csv(settings_dir / "normal-settings.csv", index=False)
    synthetic_waveform().to_csv(waveform_dir / "normal-waveform.csv", index=False)
    synthetic_waveform("CYCLE-OVERSHOOT-001", "overshoot").to_csv(
        waveform_dir / "overshoot-waveform.csv", index=False
    )
    synthetic_waveform("CYCLE-UNDERSHOOT-001", "undershoot").to_csv(
        waveform_dir / "undershoot-waveform.csv", index=False
    )
    (expected_dir / "README.txt").write_text(
        "Synthetic waveforms are generated for UI and pipeline validation only.\n",
        encoding="utf-8",
    )

"""복수 사이클 최적화의 실행 시간을 측정한다.

사용법:
    python scripts/measure_optimization_cost.py 20
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.import_service.sample_data import synthetic_waveform  # noqa: E402
from app.services.optimization.optimizer import (  # noqa: E402
    OptimizationObjectives,
    optimize_candidates,
)
from app.services.simulation.simulator import FasteningSettings  # noqa: E402

BUDGET_SECONDS = 10.0


def main() -> int:
    cycle_count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    base = synthetic_waveform()
    waveforms = []
    for index in range(cycle_count):
        frame = base.copy()
        frame["torque"] = frame["torque"] * (1.0 + 0.01 * ((index % 5) - 2))
        waveforms.append(frame)

    settings = FasteningSettings(
        target_speed=820.0,
        target_torque=1.2,
        clamp_rising_time=100.0,
        torque_hold_time=30.0,
    )
    objectives = OptimizationObjectives(
        target_torque_min=1.14,
        target_torque_max=1.26,
        max_overshoot_percent=8.0,
        max_fastening_time=900.0,
    )

    start = time.perf_counter()
    result = optimize_candidates(waveforms, settings, objectives)
    elapsed = time.perf_counter() - start

    print(f"cycles={cycle_count}")
    print(f"evaluated={result.evaluated_count} rejected={result.rejected_count}")
    print(f"gate_mode={result.gate_mode} confidence={result.confidence_grade}")
    print(f"elapsed={elapsed:.2f}s budget={BUDGET_SECONDS:.1f}s")
    if elapsed > BUDGET_SECONDS:
        # em dash 등 비ASCII 기호는 cp949 콘솔에서 UnicodeEncodeError를 낸다.
        print("OVER BUDGET - 스펙의 2단계 접근 전환을 검토하십시오.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

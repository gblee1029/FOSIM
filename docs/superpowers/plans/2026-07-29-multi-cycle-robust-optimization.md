# 복수 사이클 강건 최적화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 반복 사이클 그룹 전체에 후보 설정을 평가하고, 최악 사이클 기준으로 제약을 판정하며, 사이클 간 산포를 점수에 반영하는 최적화기를 만든다.

**Architecture:** `group_analysis` 신규 서비스가 그룹 구성·분포 통계·이상치 배제를 담당하고, 기존 `optimization/optimizer.py`는 단일 파형 대신 파형 리스트를 받도록 확장한다. API는 그룹 요약을 명시적 필드로 노출하고, 프론트엔드는 대표 사이클 암묵 규칙을 걷어낸다.

**Tech Stack:** Python 3 / FastAPI / pandas / numpy / pytest, React + TypeScript + Vite

## Global Constraints

- 스펙 원본: `docs/superpowers/specs/2026-07-29-multi-cycle-robust-optimization-design.md`
- 하위호환: 파형 1개짜리 요청은 현재와 **동일한 결과**를 내야 한다. 기존 `backend/tests/test_api_contract.py`와 `backend/tests/test_analysis_pipeline.py`의 단언이 계속 통과해야 한다.
- 점수 총점은 100점을 유지한다: constraint 30, torque_accuracy 15, reproducibility 20, overshoot 15, stability 15, fastening_time 3, setting_change 2.
- 이상치 배제는 절대 조용히 일어나지 않는다. 모든 배제는 `cycle_id`와 사유를 응답에 싣는다.
- 배제 결과가 공집합이 되면 안 된다. 전부 배제될 상황이면 전체를 포함시키고 그 사실을 경고로 남긴다.
- 재현성 점수는 예측이 아니다. 필드명과 문구에서 "관측된 변동 하에서의 결과 산포"임을 유지한다.
- 백엔드 테스트: `cd backend; python -m pytest -q`
- 프론트엔드 테스트: `cd frontend; npm.cmd test` 및 `npm.cmd run build`

## 스펙 대비 변경 사항 1건

스펙 5절은 재현성 점수를 "관측된 산포를 후보 평가에 반영"으로 서술했다. 그대로 구현하면 **모든 후보에 같은 값이 더해져 순위를 바꾸지 못한다.** 따라서 실제 구현은 후보별로 **각 사이클에 시뮬레이션한 예측 최종 토크의 산포**를 점수화한다. 관측된 사이클 간 변동이 시뮬레이터를 통과해 만들어내는 결과 산포이므로 스펙의 의도와 일치하며, 여전히 "이 후보가 공정 산포를 줄인다"는 예측이 아니다. Task 6에서 구현한다.

## 파일 구조

**신규**

| 파일 | 책임 |
|---|---|
| `backend/app/services/group_analysis/__init__.py` | 패키지 선언 |
| `backend/app/services/group_analysis/grouping.py` | 설정 튜플 기준 사이클 그룹핑 |
| `backend/app/services/group_analysis/statistics.py` | 특징 분포, 공정능력 지수, 파형 엔벨로프 |
| `backend/app/services/group_analysis/exclusion.py` | 진단 기반 + MAD 기반 배제 |
| `backend/tests/test_group_analysis.py` | 위 3개 모듈 테스트 |
| `backend/tests/test_robust_optimizer.py` | 복수 파형 최적화 테스트 |
| `frontend/src/components/workspace/GroupOverview.tsx` | 그룹 요약 + 배제 목록 UI |

**수정**

| 파일 | 변경 |
|---|---|
| `backend/app/services/optimization/optimizer.py` | 파형 리스트 수용, 최악값 게이트, 점수 재배분, fallback 재사용 |
| `backend/app/api/routes.py` | `group_summary` 노출, 최적화 요청에 복수 파형 수용, `**analyzed_cycles[0]` 제거 |
| `backend/tests/test_analysis_pipeline.py:127` | 변경된 시그니처 반영 |
| `frontend/src/types/domain.ts` | 그룹 타입 추가 |
| `frontend/src/services/api.ts` | 복수 파형 최적화 호출 |
| `frontend/src/components/workspace/CycleSelector.tsx` | 그룹 개요 + 드릴다운 |
| `frontend/src/hooks/useFasteningWorkspace.ts` | 그룹 상태 연결 |
| `docs/limitations.md` | 과적합 관련 항목 범위 축소 |

---

### Task 1: 설정 기준 그룹핑과 동일 조건 가드

**Files:**
- Create: `backend/app/services/group_analysis/__init__.py`
- Create: `backend/app/services/group_analysis/grouping.py`
- Test: `backend/tests/test_group_analysis.py`

**Interfaces:**
- Consumes: `app.services.import_service.csv_import.ImportedCycle` (필드: `cycle_id`, `settings`, `waveform`, `metadata`, `issues`), `app.services.simulation.simulator.FasteningSettings`
- Produces: `SettingsGroup` 데이터클래스와 `group_cycles_by_settings(cycles: list[ImportedCycle]) -> list[SettingsGroup]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_group_analysis.py`를 새로 만든다.

```python
from __future__ import annotations

import pandas as pd

from app.services.group_analysis.grouping import group_cycles_by_settings
from app.services.import_service.csv_import import ImportedCycle
from app.services.simulation.simulator import FasteningSettings


def _cycle(cycle_id: str, speed: float = 820.0) -> ImportedCycle:
    return ImportedCycle(
        cycle_id=cycle_id,
        settings=FasteningSettings(
            target_speed=speed,
            target_torque=1.2,
            clamp_rising_time=100.0,
            torque_hold_time=30.0,
        ),
        waveform=pd.DataFrame({"cycle_id": [cycle_id], "time_ms": [0.0], "torque": [0.0]}),
        metadata={},
        issues=[],
    )


def test_identical_settings_form_one_group():
    groups = group_cycles_by_settings([_cycle("A"), _cycle("B"), _cycle("C")])
    assert len(groups) == 1
    assert groups[0].cycle_ids == ["A", "B", "C"]


def test_different_settings_form_separate_groups():
    groups = group_cycles_by_settings([_cycle("A"), _cycle("B", speed=900.0)])
    assert len(groups) == 2
    assert [group.cycle_ids for group in groups] == [["A"], ["B"]]


def test_group_order_follows_first_appearance():
    groups = group_cycles_by_settings([_cycle("A", 900.0), _cycle("B", 820.0), _cycle("C", 900.0)])
    assert groups[0].cycle_ids == ["A", "C"]
    assert groups[1].cycle_ids == ["B"]


def test_group_serializes_settings_and_ids():
    payload = group_cycles_by_settings([_cycle("A")])[0].to_dict()
    assert payload["cycle_ids"] == ["A"]
    assert payload["settings"]["target_speed"] == 820.0
    assert payload["cycle_count"] == 1
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.group_analysis'`

- [ ] **Step 3: 구현**

`backend/app/services/group_analysis/__init__.py`:

```python
"""Group-level analysis for repeated fastening cycles."""
```

`backend/app/services/group_analysis/grouping.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.import_service.csv_import import ImportedCycle
from app.services.simulation.simulator import FasteningSettings

GroupKey = tuple[float, float, float, float]


@dataclass(frozen=True)
class SettingsGroup:
    key: GroupKey
    settings: FasteningSettings
    cycle_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": list(self.key),
            "settings": self.settings.to_dict(),
            "cycle_ids": self.cycle_ids,
            "cycle_count": len(self.cycle_ids),
        }


def _group_key(settings: FasteningSettings) -> GroupKey:
    return (
        round(float(settings.target_speed), 4),
        round(float(settings.target_torque), 4),
        round(float(settings.clamp_rising_time), 4),
        round(float(settings.torque_hold_time), 4),
    )


def group_cycles_by_settings(cycles: list[ImportedCycle]) -> list[SettingsGroup]:
    ordered_keys: list[GroupKey] = []
    members: dict[GroupKey, list[str]] = {}
    settings_by_key: dict[GroupKey, FasteningSettings] = {}
    for cycle in cycles:
        key = _group_key(cycle.settings)
        if key not in members:
            ordered_keys.append(key)
            members[key] = []
            settings_by_key[key] = cycle.settings
        members[key].append(cycle.cycle_id)
    return [
        SettingsGroup(key=key, settings=settings_by_key[key], cycle_ids=members[key])
        for key in ordered_keys
    ]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/group_analysis/ backend/tests/test_group_analysis.py
git commit -m "feat: group cycles by fastening settings"
```

---

### Task 2: 특징 분포 통계와 공정능력 지수

**Files:**
- Create: `backend/app/services/group_analysis/statistics.py`
- Modify: `backend/tests/test_group_analysis.py`

**Interfaces:**
- Consumes: `app.services.feature_extraction.features.FasteningFeatures` (관련 필드: `final_torque`, `overshoot_percent`, `total_time`, `waveform_stability_score`, `max_torque`, `clamp_time`, `seating_torque`)
- Produces: `FeatureDistribution` 데이터클래스, `summarize_features(features_list, feature_names=None) -> dict[str, FeatureDistribution]`, `process_capability(values, lower_limit, upper_limit) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_group_analysis.py` 하단에 추가한다.

```python
from app.services.group_analysis.statistics import (
    process_capability,
    summarize_features,
)


class _Features:
    """FasteningFeatures 대역. 통계 계산에 필요한 필드만 갖는다."""

    def __init__(self, final_torque: float, total_time: float = 500.0) -> None:
        self.final_torque = final_torque
        self.total_time = total_time
        self.overshoot_percent = 2.0
        self.waveform_stability_score = 0.8


def test_summarize_reports_mean_and_spread():
    summary = summarize_features(
        [_Features(1.0), _Features(2.0), _Features(3.0)],
        feature_names=["final_torque"],
    )
    dist = summary["final_torque"]
    assert dist.mean == 2.0
    assert dist.min == 1.0
    assert dist.max == 3.0
    assert dist.count == 3
    assert dist.std > 0.0


def test_summarize_single_cycle_has_zero_std():
    summary = summarize_features([_Features(1.5)], feature_names=["final_torque"])
    assert summary["final_torque"].std == 0.0
    assert summary["final_torque"].p05 == 1.5
    assert summary["final_torque"].p95 == 1.5


def test_summarize_serializes():
    payload = summarize_features([_Features(1.0)], feature_names=["final_torque"])[
        "final_torque"
    ].to_dict()
    assert payload["feature"] == "final_torque"
    assert payload["count"] == 1


def test_capability_is_high_when_spread_is_tiny():
    values = [1.20, 1.201, 1.199, 1.2005]
    assert process_capability(values, 1.16, 1.24) > 3.0


def test_capability_is_low_when_spread_is_wide():
    values = [1.10, 1.30, 1.15, 1.28]
    assert process_capability(values, 1.16, 1.24) < 1.0


def test_capability_with_zero_spread_is_capped():
    assert process_capability([1.2, 1.2, 1.2], 1.16, 1.24) == 10.0


def test_capability_with_insufficient_samples_returns_zero():
    assert process_capability([1.2], 1.16, 1.24) == 0.0
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.group_analysis.statistics'`

- [ ] **Step 3: 구현**

`backend/app/services/group_analysis/statistics.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

DEFAULT_FEATURE_NAMES = [
    "final_torque",
    "max_torque",
    "overshoot_percent",
    "total_time",
    "clamp_time",
    "seating_torque",
    "waveform_stability_score",
]

CAPABILITY_CAP = 10.0


@dataclass(frozen=True)
class FeatureDistribution:
    feature: str
    mean: float
    std: float
    min: float
    max: float
    p05: float
    p95: float
    count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_features(
    features_list: Sequence[Any],
    feature_names: Sequence[str] | None = None,
) -> dict[str, FeatureDistribution]:
    names = list(feature_names) if feature_names else list(DEFAULT_FEATURE_NAMES)
    summary: dict[str, FeatureDistribution] = {}
    for name in names:
        values = [
            float(getattr(item, name))
            for item in features_list
            if getattr(item, name, None) is not None
        ]
        if not values:
            continue
        array = np.asarray(values, dtype=float)
        summary[name] = FeatureDistribution(
            feature=name,
            mean=float(np.mean(array)),
            std=float(np.std(array, ddof=0)),
            min=float(np.min(array)),
            max=float(np.max(array)),
            p05=float(np.percentile(array, 5)),
            p95=float(np.percentile(array, 95)),
            count=int(array.size),
        )
    return summary


def process_capability(
    values: Sequence[float],
    lower_limit: float,
    upper_limit: float,
) -> float:
    """Cpk. 표본이 2개 미만이면 0.0, 산포가 0이면 CAPABILITY_CAP을 돌려준다."""
    array = np.asarray(list(values), dtype=float)
    if array.size < 2:
        return 0.0
    sigma = float(np.std(array, ddof=1))
    mean = float(np.mean(array))
    if sigma <= 1e-12:
        return CAPABILITY_CAP
    upper = (float(upper_limit) - mean) / (3.0 * sigma)
    lower = (mean - float(lower_limit)) / (3.0 * sigma)
    return float(min(min(upper, lower), CAPABILITY_CAP))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/group_analysis/statistics.py backend/tests/test_group_analysis.py
git commit -m "feat: summarize feature distributions and process capability"
```

---

### Task 3: 파형 min-max 엔벨로프

**Files:**
- Modify: `backend/app/services/group_analysis/statistics.py`
- Modify: `backend/tests/test_group_analysis.py`

**Interfaces:**
- Consumes: `pandas.DataFrame` 파형 (컬럼 `time_ms`, `torque`)
- Produces: `WaveformEnvelope` 데이터클래스, `compute_envelope(waveforms: list[pd.DataFrame], sample_count: int = 200) -> WaveformEnvelope`

시간축을 각 파형별로 `[0, 1]`로 정규화한 뒤 공통 격자에 보간한다. 사이클마다 총 길이가 다르므로 원시 시간축으로 겹치면 정렬이 어긋난다. 출력 시간축은 격자에 **총 길이의 중앙값**을 곱해 ms로 되돌린다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_group_analysis.py` 하단에 추가한다.

```python
from app.services.group_analysis.statistics import compute_envelope


def _waveform(scale: float, duration: float = 100.0) -> pd.DataFrame:
    times = [0.0, duration / 2.0, duration]
    return pd.DataFrame({"time_ms": times, "torque": [0.0, scale, scale]})


def test_envelope_brackets_every_input():
    envelope = compute_envelope([_waveform(1.0), _waveform(2.0)], sample_count=5)
    assert len(envelope.time_ms) == 5
    for low, high in zip(envelope.torque_min, envelope.torque_max):
        assert low <= high
    assert max(envelope.torque_max) >= 2.0
    assert max(envelope.torque_min) <= 1.0


def test_envelope_median_sits_between_bounds():
    envelope = compute_envelope([_waveform(1.0), _waveform(2.0), _waveform(3.0)], sample_count=5)
    for low, mid, high in zip(envelope.torque_min, envelope.torque_median, envelope.torque_max):
        assert low <= mid <= high


def test_envelope_time_axis_uses_median_duration():
    envelope = compute_envelope([_waveform(1.0, 100.0), _waveform(1.0, 300.0)], sample_count=3)
    assert envelope.time_ms[0] == 0.0
    assert envelope.time_ms[-1] == 200.0


def test_envelope_of_single_waveform_collapses_to_that_waveform():
    envelope = compute_envelope([_waveform(2.0)], sample_count=3)
    assert envelope.torque_min == envelope.torque_max


def test_envelope_of_empty_list_is_empty():
    envelope = compute_envelope([], sample_count=3)
    assert envelope.time_ms == []
    assert envelope.to_dict()["torque_median"] == []
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_envelope'`

- [ ] **Step 3: 구현**

`backend/app/services/group_analysis/statistics.py` 상단 import에 `import pandas as pd`를 추가하고, 파일 끝에 다음을 덧붙인다.

```python
@dataclass(frozen=True)
class WaveformEnvelope:
    time_ms: list[float]
    torque_min: list[float]
    torque_max: list[float]
    torque_median: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_envelope(
    waveforms: Sequence[pd.DataFrame],
    sample_count: int = 200,
) -> WaveformEnvelope:
    usable = [frame for frame in waveforms if not frame.empty and len(frame) >= 2]
    if not usable:
        return WaveformEnvelope(time_ms=[], torque_min=[], torque_max=[], torque_median=[])

    grid = np.linspace(0.0, 1.0, int(sample_count))
    resampled: list[np.ndarray] = []
    durations: list[float] = []
    for frame in usable:
        ordered = frame.sort_values("time_ms")
        times = ordered["time_ms"].to_numpy(dtype=float)
        torques = ordered["torque"].to_numpy(dtype=float)
        span = float(times[-1] - times[0])
        durations.append(span)
        if span <= 0.0:
            resampled.append(np.full(grid.shape, float(torques[-1])))
            continue
        progress = (times - times[0]) / span
        resampled.append(np.interp(grid, progress, torques))

    stack = np.vstack(resampled)
    median_duration = float(np.median(np.asarray(durations, dtype=float)))
    return WaveformEnvelope(
        time_ms=[float(value) for value in grid * median_duration],
        torque_min=[float(value) for value in np.min(stack, axis=0)],
        torque_max=[float(value) for value in np.max(stack, axis=0)],
        torque_median=[float(value) for value in np.median(stack, axis=0)],
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: PASS (16 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/group_analysis/statistics.py backend/tests/test_group_analysis.py
git commit -m "feat: compute time-normalized waveform envelope"
```

---

### Task 4: 이상치 배제 정책

**Files:**
- Create: `backend/app/services/group_analysis/exclusion.py`
- Modify: `backend/tests/test_group_analysis.py`

**Interfaces:**
- Consumes: `app.services.diagnosis.rules.Diagnosis` (필드: `anomaly_type`, `severity`, `confidence`, ...). `severity`는 `"normal"`, `"caution"`, `"warning"` 중 하나다.
- Produces: `ExclusionEntry`, `ExclusionResult` 데이터클래스, `select_included_cycles(cycle_ids, diagnoses, final_torques, mad_threshold=3.5) -> ExclusionResult`

배제 규칙:
1. `severity == "warning"`인 사이클은 배제한다. `"caution"`은 배제하지 않는다 — 보수적으로 잡아둔 등급이라 배제하면 정상 사이클까지 잘려나간다.
2. 최종 토크의 **수정 z-점수** `0.6745 * (x - median) / MAD`가 `mad_threshold`를 넘으면 배제한다. MAD가 0이면 통계적 배제를 건너뛴다.
3. 전부 배제될 상황이면 **아무것도 배제하지 않고** 경고를 남긴다. 기준 집합이 비면 최적화 자체가 불가능하다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_group_analysis.py` 하단에 추가한다.

```python
from app.services.diagnosis.rules import Diagnosis
from app.services.group_analysis.exclusion import select_included_cycles


def _diagnosis(severity: str, anomaly_type: str = "Normal") -> Diagnosis:
    return Diagnosis(
        anomaly_type=anomaly_type,
        severity=severity,
        confidence=0.8,
        evidence_features=[],
        related_parameters=[],
        recommended_checks=[],
        description="",
    )


def test_warning_severity_is_excluded():
    result = select_included_cycles(
        ["A", "B", "C"],
        [_diagnosis("normal"), _diagnosis("warning", "Torque Overshoot"), _diagnosis("normal")],
        [1.20, 1.21, 1.19],
    )
    assert result.included_cycle_ids == ["A", "C"]
    assert result.excluded[0].cycle_id == "B"
    assert "Torque Overshoot" in result.excluded[0].detail


def test_caution_severity_is_kept():
    result = select_included_cycles(
        ["A", "B"],
        [_diagnosis("normal"), _diagnosis("caution", "Early Seating Suspected")],
        [1.20, 1.21],
    )
    assert result.included_cycle_ids == ["A", "B"]
    assert result.excluded == []


def test_statistical_outlier_is_excluded():
    ids = [f"C{index}" for index in range(10)]
    torques = [1.20, 1.201, 1.199, 1.202, 1.198, 1.20, 1.201, 1.199, 1.20, 2.50]
    result = select_included_cycles(ids, [_diagnosis("normal")] * 10, torques)
    assert "C9" not in result.included_cycle_ids
    assert result.excluded[0].reason == "statistical_outlier"


def test_zero_mad_skips_statistical_exclusion():
    ids = ["A", "B", "C"]
    result = select_included_cycles(ids, [_diagnosis("normal")] * 3, [1.2, 1.2, 1.2])
    assert result.included_cycle_ids == ids
    assert result.excluded == []


def test_never_excludes_every_cycle():
    result = select_included_cycles(
        ["A", "B"],
        [_diagnosis("warning"), _diagnosis("warning")],
        [1.20, 1.21],
    )
    assert result.included_cycle_ids == ["A", "B"]
    assert result.excluded == []
    assert result.warnings != []


def test_result_serializes_counts_and_reasons():
    payload = select_included_cycles(
        ["A", "B"],
        [_diagnosis("normal"), _diagnosis("warning")],
        [1.20, 1.21],
    ).to_dict()
    assert payload["included_count"] == 1
    assert payload["excluded_count"] == 1
    assert payload["excluded"][0]["reason"] == "diagnosis"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.group_analysis.exclusion'`

- [ ] **Step 3: 구현**

`backend/app/services/group_analysis/exclusion.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

MAD_SCALE = 0.6745


@dataclass(frozen=True)
class ExclusionEntry:
    cycle_id: str
    reason: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ExclusionResult:
    included_cycle_ids: list[str]
    excluded: list[ExclusionEntry]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "included_cycle_ids": self.included_cycle_ids,
            "included_count": len(self.included_cycle_ids),
            "excluded": [entry.to_dict() for entry in self.excluded],
            "excluded_count": len(self.excluded),
            "warnings": self.warnings,
        }


def select_included_cycles(
    cycle_ids: Sequence[str],
    diagnoses: Sequence[Any],
    final_torques: Sequence[float],
    mad_threshold: float = 3.5,
) -> ExclusionResult:
    entries: list[ExclusionEntry] = []
    excluded_ids: set[str] = set()

    for cycle_id, diagnosis in zip(cycle_ids, diagnoses):
        if getattr(diagnosis, "severity", "normal") == "warning":
            entries.append(
                ExclusionEntry(
                    cycle_id=cycle_id,
                    reason="diagnosis",
                    detail=str(getattr(diagnosis, "anomaly_type", "unknown")),
                )
            )
            excluded_ids.add(cycle_id)

    values = np.asarray(list(final_torques), dtype=float)
    if values.size >= 3:
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad > 1e-12:
            scores = MAD_SCALE * (values - median) / mad
            for cycle_id, score in zip(cycle_ids, scores):
                if cycle_id in excluded_ids:
                    continue
                if abs(float(score)) > mad_threshold:
                    entries.append(
                        ExclusionEntry(
                            cycle_id=cycle_id,
                            reason="statistical_outlier",
                            detail=f"final_torque modified z-score {float(score):.2f}",
                        )
                    )
                    excluded_ids.add(cycle_id)

    included = [cycle_id for cycle_id in cycle_ids if cycle_id not in excluded_ids]
    if not included:
        return ExclusionResult(
            included_cycle_ids=list(cycle_ids),
            excluded=[],
            warnings=[
                "모든 사이클이 배제 대상이라 배제를 적용하지 않았습니다. "
                "결과를 신뢰하기 전에 원본 데이터를 확인하십시오."
            ],
        )
    return ExclusionResult(included_cycle_ids=included, excluded=entries, warnings=[])
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest tests/test_group_analysis.py -v`
Expected: PASS (22 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/group_analysis/exclusion.py backend/tests/test_group_analysis.py
git commit -m "feat: exclude diagnosed and outlier cycles from optimization basis"
```

---

### Task 5: 최적화기가 파형 리스트를 받도록 확장

**Files:**
- Modify: `backend/app/services/optimization/optimizer.py`
- Modify: `backend/app/api/routes.py:86-91`
- Modify: `backend/tests/test_analysis_pipeline.py:127`
- Test: `backend/tests/test_robust_optimizer.py`

**Interfaces:**
- Consumes: `simulate_waveform(waveform, current_settings, candidate_settings) -> SimulationResult`, `SimulationResult.predicted_features`(`final_torque`, `overshoot_percent`, `total_time`, `waveform_stability_score`), `SimulationResult.confidence.score`
- Produces:
  - `CycleEvaluation(cycle_id: str, simulation: SimulationResult, violations: list[str])`
  - `optimize_candidates(waveforms: list[pd.DataFrame], current_settings, objectives, parameter_ranges=None) -> OptimizationResult`
  - `CandidateEvaluation`에 필드 추가: `per_cycle: list[CycleEvaluation]`, `gate_mode: str`, `confidence_grade: str`
  - `confidence_grade(cycle_count: int) -> str` — `< 5`는 `"reference"`, `< 20`은 `"moderate"`, 그 이상은 `"statistical"`

게이트 규칙: 사이클 수가 20 미만이면 `"worst"` 모드로 **모든 사이클이 제약을 만족**해야 한다. 20 이상이면 `"p95"` 모드로 극단값 하나가 전 후보를 거부하지 않도록 완화한다. 표본이 적을 때 완화하지 않는 것이 중요하다 — 적은 표본에서 최악값은 유일한 정보이며, 여기서 완화하면 근거 없이 낙관적인 결과가 나온다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_robust_optimizer.py`를 새로 만든다.

```python
from __future__ import annotations

import pandas as pd
import pytest

from app.services.import_service.sample_data import synthetic_waveform
from app.services.optimization.optimizer import (
    OptimizationObjectives,
    confidence_grade,
    optimize_candidates,
)
from app.services.simulation.simulator import FasteningSettings


def _settings() -> FasteningSettings:
    return FasteningSettings(
        target_speed=820.0,
        target_torque=1.2,
        clamp_rising_time=100.0,
        torque_hold_time=30.0,
    )


def _objectives() -> OptimizationObjectives:
    return OptimizationObjectives(
        target_torque_min=1.14,
        target_torque_max=1.26,
        max_overshoot_percent=8.0,
        max_fastening_time=900.0,
        min_stability_score=0.5,
    )


def _scaled_waveform(factor: float) -> pd.DataFrame:
    frame = synthetic_waveform().copy()
    frame["torque"] = frame["torque"] * factor
    return frame


def test_single_waveform_matches_previous_behavior():
    waveform = synthetic_waveform()
    result = optimize_candidates([waveform], _settings(), _objectives())
    assert result.recommended
    assert all(len(item.per_cycle) == 1 for item in result.recommended)


def test_every_candidate_is_evaluated_on_every_cycle():
    waveforms = [_scaled_waveform(1.0), _scaled_waveform(1.02), _scaled_waveform(0.98)]
    result = optimize_candidates(waveforms, _settings(), _objectives())
    assert result.recommended
    for candidate in result.recommended:
        assert len(candidate.per_cycle) == 3


def test_small_group_uses_worst_case_gate():
    waveforms = [_scaled_waveform(1.0), _scaled_waveform(1.02)]
    result = optimize_candidates(waveforms, _settings(), _objectives())
    assert result.recommended[0].gate_mode == "worst"


def test_rejection_records_which_cycle_failed():
    strict = OptimizationObjectives(
        target_torque_min=1.199,
        target_torque_max=1.201,
        max_overshoot_percent=0.01,
        max_fastening_time=1.0,
        min_stability_score=0.999,
    )
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), strict)
    assert result.rejected_count > 0
    assert result.rejection_details
    assert "cycle_id" in result.rejection_details[0]


def test_empty_waveform_list_is_rejected():
    with pytest.raises(ValueError):
        optimize_candidates([], _settings(), _objectives())


@pytest.mark.parametrize(
    "count,grade",
    [(1, "reference"), (4, "reference"), (5, "moderate"), (19, "moderate"), (20, "statistical")],
)
def test_confidence_grade_thresholds(count: int, grade: str):
    assert confidence_grade(count) == grade
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_robust_optimizer.py -v`
Expected: FAIL — `ImportError: cannot import name 'confidence_grade'`

- [ ] **Step 3: 구현**

`backend/app/services/optimization/optimizer.py`를 수정한다.

먼저 `CandidateEvaluation` 위에 새 데이터클래스와 헬퍼를 추가한다:

```python
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
```

`CandidateEvaluation`에 필드 3개를 추가하고 `to_dict()`를 확장한다:

```python
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
```

`simulation` 필드는 유지하되 **최악 사이클의 시뮬레이션**을 담는다. 기존 프론트엔드가 이 필드를 읽고 있으므로 제거하지 않는다.

`OptimizationResult`에 `rejection_details`를 추가한다:

```python
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
```

`optimize_candidates()` 본문을 교체한다. `_score_candidate` 호출은 Task 6에서 시그니처가 바뀌므로, 지금은 최악 사이클의 시뮬레이션 하나를 넘겨 기존 함수를 그대로 쓴다:

```python
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
                candidate, per_cycle, current_settings, objectives, gate_mode, grade,
                reason="Candidate satisfies MVP constraints across the cycle group.",
            )
        )

    if not evaluated:
        for candidate, per_cycle, group_violations in all_evaluations[: min(20, len(all_evaluations))]:
            fallback = _build_evaluation(
                candidate, per_cycle, current_settings, objectives, gate_mode, grade,
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
    score, breakdown = _score_candidate(worst.simulation, current_settings, objectives)
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
```

`_with_label()`이 새 필드를 잃지 않도록 수정한다:

```python
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
```

`backend/app/api/routes.py:86-91`의 호출을 리스트로 감싼다:

```python
    result = optimize_candidates(
        [waveform],
        settings,
        objectives,
        parameter_ranges=request.parameter_ranges,
    ).to_dict()
```

`backend/tests/test_analysis_pipeline.py:127`도 동일하게 고친다:

```python
    result = optimize_candidates([waveform], settings, objectives)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest -q`
Expected: PASS — 신규 `test_robust_optimizer.py` 7건 포함 전체 통과. 기존 `test_analysis_pipeline.py`와 `test_api_contract.py`가 계속 통과하는지 반드시 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/optimization/optimizer.py backend/app/api/routes.py backend/tests/
git commit -m "feat: evaluate optimization candidates across a cycle group"
```

---

### Task 6: 점수 재배분과 재현성 항목

**Files:**
- Modify: `backend/app/services/optimization/optimizer.py`
- Modify: `backend/tests/test_robust_optimizer.py`

**Interfaces:**
- Consumes: Task 5의 `CycleEvaluation` 리스트
- Produces: `_score_candidate(per_cycle: list[CycleEvaluation], current: FasteningSettings, objectives: OptimizationObjectives) -> tuple[float, dict[str, float]]` — 시그니처가 `SimulationResult` 단건에서 리스트로 바뀐다. `score_breakdown` 키는 `constraint`, `torque_accuracy`, `reproducibility`, `overshoot`, `stability`, `fastening_time`, `setting_change` 7개다.

배점: constraint 30, torque_accuracy 15, reproducibility 20, overshoot 15, stability 15, fastening_time 3, setting_change 2 = 100.

- `torque_accuracy`, `fastening_time`은 사이클 **평균** 기준.
- `overshoot`, `stability`는 **최악 사이클** 기준.
- `reproducibility`는 사이클 간 **예측 최종 토크 표준편차**를 목표 허용폭으로 정규화한 값. 사이클이 1개면 산포가 정의되지 않으므로 만점을 준다.
- 기존 `clamp_stability` 10점 + `hold_stability` 10점은 같은 값을 두 번 읽던 것이므로 `stability` 15점 하나로 합친다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_robust_optimizer.py` 하단에 추가한다.

```python
def test_score_breakdown_has_new_keys_and_sums_to_score():
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), _objectives())
    breakdown = result.recommended[0].score_breakdown
    assert set(breakdown) == {
        "constraint",
        "torque_accuracy",
        "reproducibility",
        "overshoot",
        "stability",
        "fastening_time",
        "setting_change",
    }
    assert result.recommended[0].score == pytest.approx(sum(breakdown.values()))


def test_score_never_exceeds_one_hundred():
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), _objectives())
    for candidate in result.all_candidates:
        assert candidate.score <= 100.0 + 1e-6


def test_single_cycle_gets_full_reproducibility():
    result = optimize_candidates([_scaled_waveform(1.0)], _settings(), _objectives())
    assert result.recommended[0].score_breakdown["reproducibility"] == pytest.approx(20.0)


def test_tight_group_scores_reproducibility_above_scattered_group():
    tight = [_scaled_waveform(1.0), _scaled_waveform(1.001), _scaled_waveform(0.999)]
    scattered = [_scaled_waveform(1.0), _scaled_waveform(1.20), _scaled_waveform(0.80)]
    tight_result = optimize_candidates(tight, _settings(), _objectives())
    scattered_result = optimize_candidates(scattered, _settings(), _objectives())
    tight_score = tight_result.all_candidates[0].score_breakdown["reproducibility"]
    scattered_score = scattered_result.all_candidates[0].score_breakdown["reproducibility"]
    assert tight_score > scattered_score
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_robust_optimizer.py -v`
Expected: FAIL — `AssertionError`로 `score_breakdown`에 `clamp_stability`/`hold_stability`가 남아 있음

- [ ] **Step 3: 구현**

`backend/app/services/optimization/optimizer.py`의 `_score_candidate()`를 통째로 교체한다.

```python
def _score_candidate(
    per_cycle: list[CycleEvaluation],
    current: FasteningSettings,
    objectives: OptimizationObjectives,
) -> tuple[float, dict[str, float]]:
    features = [item.simulation.predicted_features for item in per_cycle]
    final_torques = np.asarray([f.final_torque for f in features], dtype=float)
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
    if final_torques.size < 2:
        reproducibility = 1.0
    else:
        spread = float(np.std(final_torques, ddof=1))
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
```

`_build_evaluation()`에서 호출부를 바꾼다:

```python
    score, breakdown = _score_candidate(per_cycle, current_settings, objectives)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest -q`
Expected: PASS — 전체 통과

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/optimization/optimizer.py backend/tests/test_robust_optimizer.py
git commit -m "feat: score reproducibility and remove stability double-count"
```

---

### Task 7: API에 그룹 요약 노출

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/test_api_contract.py`

**Interfaces:**
- Consumes: Task 1~4의 `group_cycles_by_settings`, `summarize_features`, `compute_envelope`, `select_included_cycles`, `process_capability`
- Produces: `/api/import/csv`와 `/api/sample/cycle` 응답에 `group_summary` 키 추가. `/api/optimizations`가 `waveforms: list[list[dict]] | None`을 수용.

이 태스크에서는 `**analyzed_cycles[0]` 전개를 **유지한다.** 프론트엔드가 아직 최상위 `cycle`/`analysis`를 읽고 있으므로, 제거는 프론트엔드 이관 후인 Task 9에서 한다.

`group_summary` 구조:

```json
{
  "groups": [ { "key": [...], "settings": {...}, "cycle_ids": [...], "cycle_count": 3 } ],
  "is_single_group": true,
  "active_group_index": 0,
  "distributions": { "final_torque": { "mean": 1.2, "std": 0.01, ... } },
  "capability": { "final_torque_cpk": 1.83 },
  "envelope": { "time_ms": [...], "torque_min": [...], "torque_max": [...], "torque_median": [...] },
  "exclusion": { "included_cycle_ids": [...], "included_count": 2, "excluded": [...], "excluded_count": 1, "warnings": [] },
  "confidence_grade": "reference"
}
```

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_api_contract.py` 하단에 추가한다. 기존 테스트가 설정/파형 CSV를 만드는 방식을 그대로 따른다.

```python
def test_import_response_includes_group_summary():
    client = TestClient(app)
    response = client.get("/api/sample/cycle")
    assert response.status_code == 200
    summary = response.json()["group_summary"]
    assert summary["is_single_group"] is True
    assert summary["groups"][0]["cycle_count"] == 1
    assert "final_torque" in summary["distributions"]
    assert summary["exclusion"]["included_count"] == 1
    assert summary["confidence_grade"] == "reference"


def test_import_response_keeps_legacy_top_level_fields():
    client = TestClient(app)
    payload = client.get("/api/sample/cycle").json()
    assert "cycle" in payload
    assert "analysis" in payload
    assert payload["active_cycle_id"] == payload["cycle"]["cycle_id"]


def test_optimization_accepts_multiple_waveforms():
    client = TestClient(app)
    imported = client.get("/api/sample/cycle").json()
    waveform = imported["cycle"]["waveform"]
    settings = imported["cycle"]["settings"]
    response = client.post(
        "/api/optimizations",
        json={
            "waveforms": [waveform, waveform],
            "current_settings": settings,
            "objectives": {
                "target_torque_min": settings["target_torque"] * 0.95,
                "target_torque_max": settings["target_torque"] * 1.05,
                "max_overshoot_percent": 8.0,
                "max_fastening_time": 900.0,
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cycle_count"] == 2
    assert body["gate_mode"] == "worst"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_api_contract.py -v`
Expected: FAIL — `KeyError: 'group_summary'`

- [ ] **Step 3: 구현**

`backend/app/api/routes.py` 상단 import에 추가한다:

```python
from app.services.group_analysis.exclusion import select_included_cycles
from app.services.group_analysis.grouping import group_cycles_by_settings
from app.services.group_analysis.statistics import (
    compute_envelope,
    process_capability,
    summarize_features,
)
from app.services.optimization.optimizer import confidence_grade
```

`OptimizationRequest`에 복수 파형 필드를 추가한다:

```python
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
```

`run_optimization()`을 바꾼다:

```python
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
```

`_analyze_import()`에 그룹 요약을 붙인다:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; python -m pytest -q`
Expected: PASS — 전체 통과

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/routes.py backend/tests/test_api_contract.py
git commit -m "feat: expose group summary and accept multiple optimization waveforms"
```

---

### Task 8: 프론트엔드 타입과 API 클라이언트

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/scripts/test_frontend_format.mjs`

**Interfaces:**
- Consumes: Task 7의 `group_summary` 응답 구조, 최적화 응답의 `cycle_count`/`gate_mode`/`confidence_grade`/`rejection_details`
- Produces: `GroupSummary`, `SettingsGroupInfo`, `FeatureDistribution`, `ExclusionInfo`, `WaveformEnvelope` 타입. `runOptimization(waveforms: WaveformSample[][], currentSettings: FasteningSettings)`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/scripts/test_frontend_format.mjs` 하단에 추가한다. 이 스크립트가 쓰는 단언 헬퍼 이름과 호출 규약을 파일 상단에서 확인한 뒤 동일한 스타일로 맞춘다.

```javascript
// group_summary 페이로드 형태 검증
const groupSummary = {
  groups: [{ key: [820, 1.2, 100, 30], settings: {}, cycle_ids: ["A", "B"], cycle_count: 2 }],
  is_single_group: true,
  active_group_index: 0,
  distributions: { final_torque: { feature: "final_torque", mean: 1.2, std: 0.01, min: 1.19, max: 1.21, p05: 1.19, p95: 1.21, count: 2 } },
  capability: { final_torque_cpk: 1.8 },
  envelope: { time_ms: [0, 1], torque_min: [0, 1], torque_max: [0, 2], torque_median: [0, 1.5] },
  exclusion: { included_cycle_ids: ["A"], included_count: 1, excluded: [{ cycle_id: "B", reason: "diagnosis", detail: "Torque Overshoot" }], excluded_count: 1, warnings: [] },
  confidence_grade: "reference",
};

assertEqual(groupSummary.groups[0].cycle_count, 2, "group cycle_count");
assertEqual(groupSummary.exclusion.excluded[0].reason, "diagnosis", "exclusion reason");
assertEqual(groupSummary.envelope.torque_min.length, groupSummary.envelope.torque_max.length, "envelope bounds align");
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: FAIL — 헬퍼 이름이 다르면 `ReferenceError`. 상단 규약에 맞춰 헬퍼 호출을 고친 뒤 다시 실행해 통과시킨다.

- [ ] **Step 3: 구현**

`frontend/src/types/domain.ts` 하단에 추가한다:

```typescript
export type SettingsGroupInfo = {
  key: number[];
  settings: FasteningSettings;
  cycle_ids: string[];
  cycle_count: number;
};

export type FeatureDistribution = {
  feature: string;
  mean: number;
  std: number;
  min: number;
  max: number;
  p05: number;
  p95: number;
  count: number;
};

export type ExclusionEntry = {
  cycle_id: string;
  reason: string;
  detail: string;
};

export type ExclusionInfo = {
  included_cycle_ids: string[];
  included_count: number;
  excluded: ExclusionEntry[];
  excluded_count: number;
  warnings: string[];
};

export type WaveformEnvelope = {
  time_ms: number[];
  torque_min: number[];
  torque_max: number[];
  torque_median: number[];
};

export type GroupSummary = {
  groups: SettingsGroupInfo[];
  is_single_group: boolean;
  active_group_index: number;
  distributions: Record<string, FeatureDistribution>;
  capability: Record<string, number>;
  envelope: WaveformEnvelope;
  exclusion: ExclusionInfo;
  confidence_grade: string;
};
```

`ImportResponse`와 `CandidateEvaluation`, `OptimizationResult`를 확장한다:

```typescript
export type ImportResponse = AnalyzedCycle & {
  cycles?: AnalyzedCycle[];
  active_cycle_id?: string;
  group_summary?: GroupSummary;
};

export type CycleEvaluation = {
  cycle_id: string;
  simulation: SimulationResult;
  violations: string[];
};

export type CandidateEvaluation = {
  label: string;
  settings: FasteningSettings;
  score: number;
  score_breakdown: Record<string, number>;
  simulation: SimulationResult;
  reason: string;
  warnings: string[];
  per_cycle: CycleEvaluation[];
  cycle_count: number;
  gate_mode: string;
  confidence_grade: string;
};

export type OptimizationResult = {
  evaluated_count: number;
  rejected_count: number;
  recommended: CandidateEvaluation[];
  all_candidates: CandidateEvaluation[];
  rejection_details: Array<{ settings: FasteningSettings; cycle_id: string; violation: string }>;
  cycle_count: number;
  gate_mode: string;
  confidence_grade: string;
};
```

`frontend/src/services/api.ts`의 `runOptimization`을 바꾼다:

```typescript
export function runOptimization(
  waveforms: WaveformSample[][],
  currentSettings: FasteningSettings,
): Promise<OptimizationResult> {
  const target = currentSettings.target_torque;
  return request<OptimizationResult>("/optimizations", {
    method: "POST",
    body: JSON.stringify({
      waveforms,
      current_settings: currentSettings,
      objectives: {
        target_torque_min: target * 0.97,
        target_torque_max: target * 1.03,
        max_overshoot_percent: 6,
        max_fastening_time: 720,
        min_stability_score: 0.62,
        allow_target_torque_change: false,
      },
    }),
  });
}
```

`frontend/src/hooks/useFasteningWorkspace.ts`의 `runOptimization` 호출부를 찾아 단일 파형 인자를 배열로 감싼다. 최적화 기준은 **배제되지 않은 사이클만** 넘긴다:

```typescript
const includedIds = new Set(
  importResponse?.group_summary?.exclusion.included_cycle_ids ?? [],
);
const optimizationWaveforms = (importResponse?.cycles ?? [])
  .filter((entry) => includedIds.size === 0 || includedIds.has(entry.cycle.cycle_id))
  .map((entry) => entry.cycle.waveform);
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs; npm.cmd run build`
Expected: 스크립트 PASS, 타입 체크 및 빌드 성공

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/types/domain.ts frontend/src/services/api.ts frontend/src/hooks/useFasteningWorkspace.ts frontend/scripts/test_frontend_format.mjs
git commit -m "feat: type group summary and send cycle group to optimizer"
```

---

### Task 9: 그룹 개요 UI와 대표 사이클 규칙 제거

**Files:**
- Create: `frontend/src/components/workspace/GroupOverview.tsx`
- Modify: `frontend/src/components/workspace/CycleSelector.tsx`
- Modify: `frontend/src/hooks/useFasteningWorkspace.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `backend/app/api/routes.py:99-104`
- Modify: `backend/tests/test_api_contract.py`

**Interfaces:**
- Consumes: Task 8의 `GroupSummary` 타입, 기존 `AnalyzedCycle`
- Produces: `GroupOverview` 컴포넌트 — props `{ summary: GroupSummary; cycles: AnalyzedCycle[] }`

프론트엔드가 `cycles`/`group_summary`만 읽게 만든 뒤, 백엔드에서 `**analyzed_cycles[0]` 전개를 제거한다. 순서를 지켜야 중간 상태에서 앱이 깨지지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_api_contract.py`의 `test_import_response_keeps_legacy_top_level_fields`를 다음으로 **교체**한다:

```python
def test_import_response_has_no_implicit_representative_cycle():
    client = TestClient(app)
    payload = client.get("/api/sample/cycle").json()
    assert "cycle" not in payload
    assert "analysis" not in payload
    assert payload["cycles"][0]["cycle"]["cycle_id"] == payload["active_cycle_id"]
    assert "group_summary" in payload
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd backend; python -m pytest tests/test_api_contract.py::test_import_response_has_no_implicit_representative_cycle -v`
Expected: FAIL — `assert "cycle" not in payload`

- [ ] **Step 3: 구현**

`frontend/src/components/workspace/GroupOverview.tsx`를 새로 만든다. 기존 `CycleSelector.tsx`의 `Card`/`CardContent`/`CardHeader`/`CardTitle` 임포트 경로와 Tailwind 클래스 관용구를 그대로 따른다.

```tsx
import type { AnalyzedCycle, GroupSummary } from "../../types/domain";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

type Props = {
  summary: GroupSummary;
  cycles: AnalyzedCycle[];
};

const GRADE_LABEL: Record<string, string> = {
  reference: "참고 수준 (표본 5개 미만)",
  moderate: "보통 (표본 5~19개)",
  statistical: "통계적 유의 (표본 20개 이상)",
};

export function GroupOverview({ summary, cycles }: Props) {
  const finalTorque = summary.distributions.final_torque;
  const cpk = summary.capability.final_torque_cpk;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cycle group</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {!summary.is_single_group && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-2 text-amber-800">
            설정이 다른 그룹이 {summary.groups.length}개 있습니다. 최적화는 첫 번째 그룹만 사용합니다.
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Cycles</div>
            <div className="font-mono text-graphite">{cycles.length}</div>
          </div>
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Optimization basis</div>
            <div className="font-mono text-graphite">{summary.exclusion.included_count}</div>
          </div>
          {finalTorque && (
            <>
              <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
                <div className="text-slate-400">Final torque mean</div>
                <div className="font-mono text-graphite">{finalTorque.mean.toFixed(3)}</div>
              </div>
              <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
                <div className="text-slate-400">Final torque std</div>
                <div className="font-mono text-graphite">{finalTorque.std.toFixed(4)}</div>
              </div>
            </>
          )}
          {cpk !== undefined && (
            <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
              <div className="text-slate-400">Cpk</div>
              <div className="font-mono text-graphite">{cpk.toFixed(2)}</div>
            </div>
          )}
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Confidence</div>
            <div className="text-graphite">{GRADE_LABEL[summary.confidence_grade] ?? summary.confidence_grade}</div>
          </div>
        </div>
        {summary.exclusion.excluded.length > 0 && (
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="mb-1 text-slate-400">
              최적화 기준에서 제외 {summary.exclusion.excluded_count}건
            </div>
            <ul className="space-y-1">
              {summary.exclusion.excluded.map((entry) => (
                <li key={entry.cycle_id} className="font-mono text-graphite">
                  {entry.cycle_id} — {entry.reason}: {entry.detail}
                </li>
              ))}
            </ul>
          </div>
        )}
        {summary.exclusion.warnings.map((warning) => (
          <div key={warning} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-2 text-amber-800">
            {warning}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

`CycleSelector.tsx`의 드롭다운 옵션에 배제 표시를 붙인다. props에 `excludedIds: string[]`를 추가하고 옵션 라벨을 바꾼다:

```tsx
{cycles.map((entry) => {
  const excluded = excludedIds.includes(entry.cycle.cycle_id);
  return (
    <option key={entry.cycle.cycle_id} value={entry.cycle.cycle_id}>
      {entry.cycle.cycle_id}
      {excluded ? " (제외됨)" : ""}
    </option>
  );
})}
```

`useFasteningWorkspace.ts`에서 최상위 `cycle`/`analysis` 접근을 전부 `cycles`와 `activeCycleId` 기반으로 바꾼다. 활성 사이클은 다음으로 얻는다:

```typescript
const activeCycle =
  importResponse?.cycles?.find((entry) => entry.cycle.cycle_id === activeCycleId) ??
  importResponse?.cycles?.[0];
```

`App.tsx`에 `GroupOverview`를 렌더링한다. `group_summary`가 있을 때만 그린다.

프론트엔드 빌드가 통과한 뒤에야 백엔드를 고친다. `backend/app/api/routes.py`의 `_analyze_import()`에서 전개를 제거한다:

```python
    response = {
        "cycles": analyzed_cycles,
        "active_cycle_id": analyzed_cycles[0]["cycle"]["cycle_id"],
        "group_summary": _build_group_summary(imported_cycles),
    }
```

`_store_import()`가 `payload["cycle"]`을 참조하던 폴백을 정리한다:

```python
def _store_import(payload: dict[str, Any]) -> None:
    for entry in payload["cycles"]:
        _store_import_entry(entry)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend; npm.cmd run build`
Expected: 빌드 성공

Run: `cd backend; python -m pytest -q`
Expected: PASS — 전체 통과. 기존 `test_api_contract.py`에서 최상위 `cycle`을 읽던 단언이 남아 있으면 `cycles[0]["cycle"]`로 고친다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src backend/app/api/routes.py backend/tests/test_api_contract.py
git commit -m "feat: show cycle group overview and drop implicit representative cycle"
```

---

### Task 10: 성능 측정과 문서 갱신

**Files:**
- Create: `scripts/measure_optimization_cost.py`
- Modify: `docs/limitations.md`
- Modify: `docs/optimization-model.md`

**Interfaces:**
- Consumes: Task 5~6의 `optimize_candidates`
- Produces: 측정 스크립트. 별도 코드 의존 없음.

스펙은 후보 80개 × 사이클 20개 = 시뮬레이터 1600회 호출을 **추정치**로 두었다. 실측해 예산을 확정한다. 목표는 로컬 데스크톱에서 **10초 이내**다. 초과하면 스펙의 2단계 접근으로 전환할지 판단한다.

- [ ] **Step 1: 측정 스크립트 작성**

`scripts/measure_optimization_cost.py`:

```python
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
        print("OVER BUDGET — 스펙의 2단계 접근 전환을 검토하십시오.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 측정 실행**

Run: `python scripts/measure_optimization_cost.py 20`
Expected: `elapsed` 값 출력. 예산 초과 시 종료코드 1.

**측정값을 기록하고, 예산을 넘으면 여기서 멈춰 사용자에게 2단계 접근 전환 여부를 확인한다.** 임의로 최적화하지 않는다.

- [ ] **Step 3: 문서 갱신**

`docs/limitations.md`의 다음 항목을

```text
- A single waveform cannot prove the true effect of setting changes.
```

이렇게 바꾼다:

```text
- Optimization now evaluates candidates across a repeated-cycle group, which
  removes overfitting to one arbitrarily chosen waveform and quantifies
  cycle-to-cycle scatter. It does not reduce the simulator's own model error.
  Proving the true effect of a setting change still requires controlled
  before/after trials on real SH-2 equipment.
```

`docs/optimization-model.md`의 `## Scoring` 절을 새 배점으로 교체하고, `## Constraint Filter` 절에 그룹 게이트 설명을 추가한다:

```text
## Scoring

Total score is 100 points:

- constraint satisfaction: 30,
- target torque accuracy: 15 (group mean),
- reproducibility: 20 (predicted final-torque spread across cycles),
- overshoot: 15 (worst cycle),
- stability: 15 (worst cycle),
- fastening time: 3 (group mean),
- setting change size: 2.

Reproducibility scores the spread of predicted outcomes under the observed
cycle-to-cycle variation. It is not a prediction that a candidate reduces
process scatter.
```

- [ ] **Step 4: 문서 확인**

Run: `cd backend; python -m pytest -q`
Expected: PASS — 문서 변경은 테스트에 영향이 없어야 한다.

- [ ] **Step 5: 커밋**

```bash
git add scripts/measure_optimization_cost.py docs/limitations.md docs/optimization-model.md
git commit -m "chore: measure optimization cost and update model docs"
```

---

## 자체 검토 결과

**스펙 커버리지**

| 스펙 절 | 담당 태스크 |
|---|---|
| 1. 그룹 구성과 동일 조건 가드 | Task 1, Task 7(`is_single_group`), Task 9(경고 UI) |
| 2. 그룹 집계 분석 서비스 | Task 2(분포·Cpk), Task 3(엔벨로프) |
| 3. 이상치 배제 정책 | Task 4, Task 7(응답), Task 9(UI) |
| 4. 강건 최적화기 | Task 5(리스트 수용·게이트·탈락 사유·fallback 재사용) |
| 5. 점수 재배분 | Task 6 |
| 6. API와 프론트엔드 | Task 7, Task 8, Task 9 |
| 검증 | 각 태스크의 테스트 + Task 10(성능) |
| 리스크와 한계 | Task 10(문서 갱신) |

**미해결로 남긴 것**

스펙 6절의 "후보 카드에 `20개 중 17개 기준, 최악 사이클에서도 제약 만족` 형태의 근거 표기"는 Task 9에서 `GroupOverview`에 그룹 단위로 표시하되, **후보 카드 자체**에는 표시하지 않는다. 후보 카드 컴포넌트를 아직 읽지 않았으므로 정확한 수정 지점을 특정할 수 없다. 구현자는 Task 9에서 후보 카드 컴포넌트를 찾아 `candidate.cycle_count`와 `candidate.gate_mode`를 한 줄로 덧붙인다.

**타입 일관성 확인**

- `CandidateEvaluation.per_cycle`은 Task 5에서 정의되고 Task 6, 8, 9에서 동일한 이름으로 쓰인다.
- `confidence_grade`는 Task 5의 함수명이자 Task 5/7/8의 필드명이다. 함수는 `optimizer.py`에서, 필드는 응답 JSON에서 쓰이며 충돌하지 않는다.
- `_score_candidate`의 시그니처는 Task 5에서 단건 `SimulationResult`를 받다가 Task 6에서 `list[CycleEvaluation]`으로 바뀐다. Task 5 완료 시점에 테스트가 통과하고 Task 6에서 함께 바뀌므로 중간 상태에 깨짐이 없다.
- `select_included_cycles`의 3번째 인자는 Task 4와 Task 7 모두 `final_torques`다.

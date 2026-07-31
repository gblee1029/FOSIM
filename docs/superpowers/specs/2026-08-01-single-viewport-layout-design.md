# 단일 뷰포트 레이아웃 설계

**목표:** 페이지 스크롤 없이 FHD 한 화면에서 전체 워크스페이스를 볼 수 있게 한다.

## 배경

현재 `App.tsx`는 루트가 `min-h-screen`이라 내용이 늘어나면 페이지 전체가 세로로 늘어난다.
콘텐츠 총 높이가 약 1500px이라 FHD(실사용 약 900px)에서 항상 스크롤이 생긴다.

세로로 쌓이는 구성은 다음과 같다.

- 좌측 레일: ImportPanel, CycleSelector, GroupOverview, DiagnosisPanel, SimulationNotes (5개)
- 중앙: WaveformChart(`h-[520px]` 고정) + FeatureTable(8행)
- 우측: SettingsPanel, Actions, CandidateCards

## 제약

- 기준 해상도는 **1920x1080**. 브라우저 크롬을 제외한 실사용 높이 약 900px.
- 항상 보여야 하는 것: **파형 비교 차트, 설정 슬라이더, 특징 비교 표, 추천 후보 카드**.
- 보조 패널 5개(Import, CycleSelector, GroupOverview, Diagnosis, SimulationNotes)는 탭으로 묶어도 된다.
- **페이지 전체 스크롤은 없다.** 내용이 할당 높이를 넘치면 해당 패널 안에서만 스크롤한다.
- 기존 프론트엔드 테스트 방식(`scripts/test_frontend_format.mjs`)을 따른다.

## 기각한 대안

- **2컬럼 + 상단 유틸리티 바**: 차트가 가장 넓어지지만 보조 정보가 전부 드롭다운에 숨는다.
  그룹 요약과 제외 내역은 최적화 결과를 해석하는 근거라, 접근에 클릭이 필요해지면 놓치기 쉽다.
- **밀도 축소만**: 구조를 그대로 두고 여백·폰트만 줄이는 방식. 제외 목록이나 후보가 늘면
  즉시 다시 넘치므로 근본 해결이 아니다.

## 1. 레이아웃 골격

루트를 고정 높이 플렉스 컬럼으로 바꿔 페이지 스크롤을 없앤다.

```
main            h-screen flex flex-col overflow-hidden
├ header        shrink-0   (약 64px)
├ error banner  shrink-0   (조건부)
└ workspace     flex-1 min-h-0 grid xl:grid-cols-[280px_minmax(0,1fr)_360px]
   ├ 좌측 레일   min-h-0 flex flex-col
   ├ 중앙       min-h-0 flex flex-col
   └ 우측 레일   min-h-0 flex flex-col
```

모든 플렉스 자식에 `min-h-0`을 준다. 플렉스 아이템의 기본값 `min-height:auto`는 내용이
컨테이너보다 커질 때 컨테이너를 밀어내며, 이것이 현재 스크롤이 생기는 근본 원인이다.

헤더는 제목 블록과 통계 타일 4개를 한 줄로 배치해 현재 약 110px에서 약 64px로 줄인다.
우측 레일의 **Actions 카드(Optimize / Export)를 헤더로 옮긴다.** 전역 동작이라 헤더가
자연스럽고, 우측 레일에서 약 90px을 회수한다.

## 2. 좌측 탭 레일

신규 컴포넌트 `frontend/src/components/workspace/SidePanelTabs.tsx`.

보조 패널 5개를 성격에 따라 탭 3개로 묶는다.

| 탭 | 내용 |
|---|---|
| 입력 | ImportPanel + CycleSelector |
| 그룹 | GroupOverview |
| 분석 | DiagnosisPanel + SimulationNotes |

- 탭 선택 상태는 `SidePanelTabs` 내부 `useState`로 보관한다. 워크스페이스 데이터와 무관한
  순수 표시 상태이므로 `useFasteningWorkspace`를 건드리지 않는다.
- 제외된 사이클이 있으면 **그룹 탭에 개수 배지**를 띄운다. 탭에 가려 놓치는 것을 막는다.
- 탭 본문은 `flex-1 min-h-0 overflow-y-auto`. 넘칠 때 이 영역만 스크롤된다.
- CycleSelector는 사이클이 2개 이상일 때만, GroupOverview는 `group_summary`가 있을 때만
  렌더링하던 기존 조건을 유지한다. 탭에 표시할 내용이 하나도 없으면 그 탭은 비활성으로 둔다.

**인터페이스**

```typescript
type SidePanelTabsProps = {
  importPanel: ReactNode;
  cycleSelector?: ReactNode;
  groupOverview?: ReactNode;
  diagnosis?: ReactNode;
  notes?: ReactNode;
  excludedCount?: number;
};
```

탭 구성 계산은 순수 함수 `sidePanelTabs(props)`로 분리해 테스트에서 직접 import한다.

```typescript
type SidePanelTab = {
  id: "input" | "group" | "analysis";
  label: string;
  content: ReactNode[];   // 렌더링할 패널들. 비어 있으면 disabled가 true다.
  badge?: number;         // 그룹 탭의 제외 건수. 0이면 생략한다.
  disabled: boolean;      // content가 비었을 때 true
};

function sidePanelTabs(props: SidePanelTabsProps): SidePanelTab[];
```

항상 탭 3개를 순서대로 돌려준다. 내용이 없는 탭도 배열에서 빼지 않고 `disabled: true`로
표시한다 — 탭의 위치가 상황에 따라 움직이면 사용자가 위치를 기억할 수 없기 때문이다.

기본 활성 탭은 **입력**이다. ImportPanel은 항상 렌더링되므로 이 탭은 절대 비활성이 되지
않는다. 활성 탭이 비활성으로 바뀌면(예: 그룹 탭을 보던 중 새 임포트로 `group_summary`가
사라짐) 입력 탭으로 되돌린다.

## 3. 중앙·우측 컬럼

```
중앙   차트 카드     flex-1 min-h-0      ← 남은 높이 전부
      특징 표       shrink-0            (8행, 약 280px)

우측   설정 슬라이더  shrink-0
      후보 카드     flex-1 min-h-0 overflow-y-auto
```

## 4. 차트 가변 높이

`WaveformChart`의 `h-[520px]`을 `h-full`로 바꾼다. 다만 이것만으로는 부족하다.

컨테이너 높이는 창 크기 변화 없이도 바뀐다(탭 전환, 특징 표 등장/소멸, 에러 배너 표시).
현재는 `window.resize`만 듣고 있어 그런 경우 ECharts가 리사이즈되지 않는다.
**ResizeObserver로 교체한다.**

함께 고칠 문제가 있다. 현재 `useEffect`가 `[option]`에 의존해 파형이 바뀔 때마다 차트를
`dispose` 후 재생성한다. 사용자의 dataZoom(확대) 상태가 매번 초기화되고 비용도 크다.
리사이즈 로직을 손대는 김에 다음으로 분리한다.

- **init / dispose / ResizeObserver 등록**: 마운트 시 1회 (`[]` 의존)
- **`setOption`**: `[option]` 의존인 별도 effect

## 5. 테스트

`scripts/test_frontend_format.mjs`는 `src/lib`의 실제 함수를 import해 `assert.equal`로
검증하거나, 소스를 읽어 `assert.match`로 구조를 고정하는 파일이다. 같은 방식을 따른다.
리터럴을 만들어 그 리터럴을 단언하면 제품 코드를 거치지 않으므로 금지한다.

- `sidePanelTabs()`를 직접 import해 검증
  - 모든 내용이 있을 때 탭 3개가 나온다
  - `excludedCount`가 있으면 그룹 탭에 배지 값이 실린다
  - `groupOverview`가 없으면 그룹 탭이 `disabled`가 되고, 배열에서 빠지지 않는다
  - `excludedCount`가 0이면 배지가 생략된다
- `App.tsx` 소스: `h-screen`과 `overflow-hidden`이 있고 `min-h-screen`이 없다
- `WaveformChart.tsx` 소스: `ResizeObserver`가 있고 `h-[520px]`이 없다
- `npm.cmd run build`로 타입 체크와 번들 생성이 통과한다

## 높이 예산 (FHD 900px)

| 영역 | 높이 |
|---|---|
| 헤더 | 64 |
| 상하 패딩·갭 | 32 |
| 특징 표 | 280 |
| 카드 헤더·여백 | 24 |
| **차트에 남는 높이** | **약 500** |

현재 고정값 520px과 거의 같아 차트 가독성 손실이 없다.

## 범위 밖

- 1366x768 이하 대응. FHD를 기준으로 하며, 그보다 작은 화면은 패널 내부 스크롤로 동작한다.
- 반응형 모바일 레이아웃. 기존 `xl:` 브레이크포인트 미만 동작(1컬럼 세로 스택)은 유지한다.
- 차트 자체의 시각 디자인 변경.

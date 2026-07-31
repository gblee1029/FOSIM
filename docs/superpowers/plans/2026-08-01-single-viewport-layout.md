# 단일 뷰포트 레이아웃 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 페이지 스크롤 없이 FHD 한 화면에서 전체 워크스페이스를 볼 수 있게 만든다.

**Architecture:** 루트를 `h-screen` 플렉스 컬럼으로 바꾸고 모든 플렉스 자식에 `min-h-0`을 준다. 좌측 보조 패널 5개는 탭 3개로 묶고, 파형 차트는 고정 높이 대신 남은 공간을 채운다. 넘치는 내용은 페이지가 아니라 해당 패널 안에서만 스크롤한다.

**Tech Stack:** React 19 + TypeScript + Vite + Tailwind, ECharts 6

## Global Constraints

- 스펙 원본: `docs/superpowers/specs/2026-08-01-single-viewport-layout-design.md`
- 기준 해상도 **1920x1080**, 브라우저 크롬 제외 실사용 높이 약 900px.
- 항상 보여야 하는 것: 파형 비교 차트, 설정 슬라이더, 특징 비교 표, 추천 후보 카드.
- **페이지 전체 스크롤은 없다.** 넘치면 해당 패널 안에서만 스크롤한다.
- 기존 `xl:` 브레이크포인트 미만의 1컬럼 세로 스택 동작은 유지한다.
- 프론트엔드 테스트: `cd frontend; node scripts/test_frontend_format.mjs`
- 프론트엔드 빌드: `cd frontend; npm.cmd run build`
- 백엔드는 이 작업에서 건드리지 않는다.

## 스펙 대비 변경 사항 1건

스펙 5절은 `sidePanelTabs()`를 `SidePanelTabs.tsx`에서 분리해 테스트에서 직접 import한다고 썼다. 그런데 `scripts/test_frontend_format.mjs`가 도는 Node의 타입 스트리핑은 **JSX를 처리하지 못한다.** 실제로 이 파일은 `.ts`만 import하고 `.tsx`는 `readFileSync` + `assert.match`로 검사한다(`format.ts`, `liveSimulation.ts` 대 `App.tsx`, `CandidateCards.tsx`).

따라서 순수 함수는 JSX가 없는 **`frontend/src/lib/sidePanelTabs.ts`** 에 둔다. 컴포넌트는 이 함수를 import해 쓴다. 스펙의 의도(제품 코드를 실제로 거치는 테스트)를 그대로 지키면서 기존 관례와도 맞는다.

## 파일 구조

**신규**

| 파일 | 책임 |
|---|---|
| `frontend/src/lib/sidePanelTabs.ts` | 탭 구성 계산 순수 함수와 타입 |
| `frontend/src/components/workspace/SidePanelTabs.tsx` | 탭 UI와 선택 상태 |

**수정**

| 파일 | 변경 |
|---|---|
| `frontend/src/components/WaveformChart.tsx` | 가변 높이, ResizeObserver, init/setOption 분리 |
| `frontend/src/App.tsx` | 레이아웃 골격 전환, 헤더 압축, Actions 헤더 이동, 탭 레일 배선 |
| `frontend/scripts/test_frontend_format.mjs` | 신규 검증 추가, 변경된 단언 갱신 |

---

### Task 1: 탭 구성 순수 함수와 SidePanelTabs 컴포넌트

**Files:**
- Create: `frontend/src/lib/sidePanelTabs.ts`
- Create: `frontend/src/components/workspace/SidePanelTabs.tsx`
- Modify: `frontend/scripts/test_frontend_format.mjs`

**Interfaces:**
- Produces:
  - `type SidePanelTabId = "input" | "group" | "analysis"`
  - `type SidePanelTab = { id: SidePanelTabId; label: string; content: ReactNode[]; badge?: number; disabled: boolean }`
  - `type SidePanelTabsProps = { importPanel?: ReactNode; cycleSelector?: ReactNode; groupOverview?: ReactNode; diagnosis?: ReactNode; notes?: ReactNode; excludedCount?: number }`
  - `sidePanelTabs(props: SidePanelTabsProps): SidePanelTab[]` — 항상 길이 3, 순서 고정
  - `<SidePanelTabs {...SidePanelTabsProps} />`

항상 탭 3개를 순서대로 돌려준다. 내용이 없는 탭도 배열에서 빼지 않고 `disabled: true`로 표시한다 — 탭 위치가 상황에 따라 움직이면 사용자가 위치를 기억할 수 없다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/scripts/test_frontend_format.mjs`의 import 블록 맨 아래에 추가한다:

```javascript
import { sidePanelTabs } from "../src/lib/sidePanelTabs.ts";
```

`console.log(...)` 줄 **바로 위**에 추가한다:

```javascript
const fullTabs = sidePanelTabs({
  importPanel: "IMPORT",
  cycleSelector: "CYCLES",
  groupOverview: "GROUP",
  diagnosis: "DIAGNOSIS",
  notes: "NOTES",
  excludedCount: 2,
});
assert.equal(fullTabs.length, 3);
assert.deepEqual(
  fullTabs.map((tab) => tab.id),
  ["input", "group", "analysis"],
);
assert.deepEqual(fullTabs[0].content, ["IMPORT", "CYCLES"]);
assert.deepEqual(fullTabs[2].content, ["DIAGNOSIS", "NOTES"]);
assert.equal(fullTabs[1].badge, 2);
assert.equal(fullTabs.every((tab) => tab.disabled === false), true);

// 내용이 없는 탭도 배열에서 빠지지 않는다. 탭 위치는 항상 고정이다.
const sparseTabs = sidePanelTabs({ importPanel: "IMPORT" });
assert.equal(sparseTabs.length, 3);
assert.equal(sparseTabs[0].disabled, false);
assert.equal(sparseTabs[1].disabled, true);
assert.equal(sparseTabs[2].disabled, true);

// 제외가 0건이면 배지를 달지 않는다.
assert.equal(sidePanelTabs({ importPanel: "IMPORT", excludedCount: 0 })[1].badge, undefined);

// 입력 탭은 ImportPanel이 항상 있으므로 비활성이 되지 않는다.
assert.equal(sidePanelTabs({ importPanel: "IMPORT" })[0].disabled, false);
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: FAIL — `ERR_MODULE_NOT_FOUND: ../src/lib/sidePanelTabs.ts`

- [ ] **Step 3: 순수 함수 구현**

`frontend/src/lib/sidePanelTabs.ts`를 새로 만든다.

```typescript
import type { ReactNode } from "react";

export type SidePanelTabId = "input" | "group" | "analysis";

export type SidePanelTab = {
  id: SidePanelTabId;
  label: string;
  /** 렌더링할 패널들. 비어 있으면 disabled가 true다. */
  content: ReactNode[];
  /** 그룹 탭의 제외 건수. 0이거나 없으면 생략한다. */
  badge?: number;
  disabled: boolean;
};

export type SidePanelTabsProps = {
  importPanel?: ReactNode;
  cycleSelector?: ReactNode;
  groupOverview?: ReactNode;
  diagnosis?: ReactNode;
  notes?: ReactNode;
  excludedCount?: number;
};

function present(...items: Array<ReactNode | undefined>): ReactNode[] {
  return items.filter((item) => item !== undefined && item !== null && item !== false);
}

export function sidePanelTabs(props: SidePanelTabsProps): SidePanelTab[] {
  const input = present(props.importPanel, props.cycleSelector);
  const group = present(props.groupOverview);
  const analysis = present(props.diagnosis, props.notes);

  const groupTab: SidePanelTab = {
    id: "group",
    label: "그룹",
    content: group,
    disabled: group.length === 0,
  };
  if (props.excludedCount) {
    groupTab.badge = props.excludedCount;
  }

  return [
    { id: "input", label: "입력", content: input, disabled: input.length === 0 },
    groupTab,
    { id: "analysis", label: "분석", content: analysis, disabled: analysis.length === 0 },
  ];
}
```

- [ ] **Step 4: 컴포넌트 구현**

`frontend/src/components/workspace/SidePanelTabs.tsx`를 새로 만든다. 탭 선택은 내부 상태로만 관리한다.

```tsx
import { useEffect, useState } from "react";

import { sidePanelTabs, type SidePanelTabId, type SidePanelTabsProps } from "../../lib/sidePanelTabs";

export function SidePanelTabs(props: SidePanelTabsProps) {
  // useMemo를 쓰지 않는다. props는 매 렌더마다 새 JSX 객체를 담고 오므로 의존 배열이
  // 항상 바뀌어 메모이제이션이 되지 않는다. 계산도 배열 3개 만드는 수준이라 값싸다.
  const tabs = sidePanelTabs(props);
  const [activeId, setActiveId] = useState<SidePanelTabId>("input");

  // 보던 탭이 비활성으로 바뀌면(예: 새 임포트로 group_summary가 사라짐) 입력 탭으로 되돌린다.
  const activeTab = tabs.find((tab) => tab.id === activeId);
  useEffect(() => {
    if (activeTab?.disabled) setActiveId("input");
  }, [activeTab?.disabled]);

  const shown = activeTab && !activeTab.disabled ? activeTab : tabs[0];

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-md border border-slate-200 bg-white shadow-sm">
      <div className="flex shrink-0 gap-1 border-b border-slate-100 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            disabled={tab.disabled}
            onClick={() => setActiveId(tab.id)}
            className={
              "flex flex-1 items-center justify-center gap-1 rounded px-2 py-1.5 text-xs font-medium transition " +
              (tab.id === shown?.id
                ? "bg-graphite text-white"
                : tab.disabled
                  ? "cursor-not-allowed text-slate-300"
                  : "text-steel hover:bg-slate-100")
            }
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span className="rounded-full bg-amber-100 px-1.5 text-[10px] font-semibold text-amber-800">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-2">
        {shown?.content.map((node, index) => <div key={index}>{node}</div>)}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: PASS

Run: `cd frontend; npm.cmd run build`
Expected: 타입 체크와 번들 생성 통과

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/sidePanelTabs.ts frontend/src/components/workspace/SidePanelTabs.tsx frontend/scripts/test_frontend_format.mjs
git commit -m "feat: add tabbed side panel container"
```

---

### Task 2: 파형 차트 가변 높이

**Files:**
- Modify: `frontend/src/components/WaveformChart.tsx`
- Modify: `frontend/scripts/test_frontend_format.mjs`

**Interfaces:**
- Consumes: 없음 (Task 1과 독립)
- Produces: `WaveformChart`의 props는 그대로다. 컨테이너가 `h-full min-h-[320px] w-full`이 된다.

`h-full`만으로는 부족하다. 컨테이너 높이는 창 크기 변화 없이도 바뀌는데(탭 전환, 특징 표 등장, 에러 배너 표시) 현재는 `window.resize`만 듣고 있어 ECharts가 리사이즈되지 않는다.

`min-h-[320px]`을 함께 두는 이유는 두 가지다. Task 3 전까지 부모가 auto 높이라 `h-full`이 0으로 접히는 것을 막고, Task 3 이후에는 아주 작은 뷰포트에서 차트가 뭉개지지 않게 하는 바닥값이 된다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/scripts/test_frontend_format.mjs`의 소스 읽기 블록에 추가한다:

```javascript
const waveformSource = readFileSync(
  new URL("../src/components/WaveformChart.tsx", import.meta.url),
  "utf8",
);
```

단언 블록에 추가한다:

```javascript
assert.match(waveformSource, /ResizeObserver/);
assert.doesNotMatch(waveformSource, /h-\[520px\]/);
// init/dispose는 마운트 1회, setOption은 별도 effect여야 dataZoom 상태가 보존된다.
assert.match(waveformSource, /replaceMerge/);
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: FAIL — `The input did not match the regular expression /ResizeObserver/`

- [ ] **Step 3: 구현**

`frontend/src/components/WaveformChart.tsx`를 세 군데 고친다. import 줄과 `option`을 만드는 `useMemo`는 그대로 둔다.

**(1)** 기존 21행 `const ref = useRef<HTMLDivElement | null>(null);` **바로 아래**에 한 줄만 추가한다. 이 줄은 옮기지 말고 그 자리에 둔다:

```tsx
  const chartRef = useRef<echarts.ECharts | null>(null);
```

**(2)** 기존 `useEffect`(106~116행) 전체를 아래 두 개의 `useEffect`로 교체한다:

```tsx
  // 차트 인스턴스는 마운트 시 1회만 만든다. 매번 재생성하면 사용자의 확대(dataZoom)
  // 상태가 초기화된다.
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const chart = echarts.init(element);
    chartRef.current = chart;

    // 창 크기가 그대로여도 컨테이너 높이는 바뀐다(탭 전환, 특징 표 등장 등).
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    // 예측 파형이 생기거나 사라지면 series 개수가 바뀌므로 series만 교체한다.
    // 통째로 notMerge하면 dataZoom 위치까지 초기화된다.
    chartRef.current?.setOption(option, { replaceMerge: ["series"] });
  }, [option]);
```

**(3)** 마지막 반환문(118행)을 바꾼다:

```tsx
  return <div ref={ref} className="h-full min-h-[320px] w-full" />;
```

`ref` 선언은 (1)에서 건드리지 않았으므로 파일에 단 하나만 있어야 한다. 두 번 선언되면 빌드가 깨진다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: PASS

Run: `cd frontend; npm.cmd run build`
Expected: 통과

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/WaveformChart.tsx frontend/scripts/test_frontend_format.mjs
git commit -m "feat: make waveform chart fill available height"
```

---

### Task 3: App 레이아웃 골격 전환

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/scripts/test_frontend_format.mjs`

**Interfaces:**
- Consumes: Task 1의 `<SidePanelTabs />`, Task 2의 가변 높이 `<WaveformChart />`
- Produces: 없음 (최종 통합)

기존 테스트 단언 2개가 이 태스크에서 깨진다. 승인된 변경이며 회귀가 아니다.

- `xl:grid-cols-[260px_minmax(0,1fr)_360px]` → 탭 레일 때문에 `280px`로 넓힌다.
- `Station overview` → 좌측 레일 제목이 탭 바로 대체되어 사라진다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/scripts/test_frontend_format.mjs`에서 기존 단언 2줄을 찾아 **교체**한다.

`assert.match(appSource, /xl:grid-cols-\[260px_minmax\(0,1fr\)_360px\]/);` 를 아래로 바꾼다:

```javascript
assert.match(appSource, /xl:grid-cols-\[280px_minmax\(0,1fr\)_360px\]/);
```

`assert.match(appSource, /Station overview/);` 를 아래로 바꾼다:

```javascript
assert.match(appSource, /SidePanelTabs/);
```

그리고 단언 블록에 추가한다:

```javascript
// 페이지 전체가 스크롤되지 않아야 한다.
assert.match(appSource, /h-screen/);
assert.match(appSource, /overflow-hidden/);
assert.doesNotMatch(appSource, /min-h-screen/);
// Actions는 헤더로 옮겨졌으므로 우측 레일에 Actions 카드가 없다.
assert.doesNotMatch(appSource, /<CardTitle>Actions<\/CardTitle>/);
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: FAIL — `The input did not match the regular expression /xl:grid-cols-\[280px_minmax\(0,1fr\)_360px\]/`

- [ ] **Step 3: 구현**

`frontend/src/App.tsx`의 `import` 블록에 한 줄 추가한다:

```tsx
import { SidePanelTabs } from "./components/workspace/SidePanelTabs";
```

`return (` 부터 파일 끝의 `}` 직전까지를 통째로 아래로 교체한다:

```tsx
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-[#eef1ed] text-graphite">
      <header className="shrink-0 border-b border-slate-300 bg-[#f8faf6]">
        <div className="mx-auto flex max-w-[1640px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-steel">
              <Activity size={14} />
              SH-2 Smart Manager MVP
            </div>
            {/* 제목과 사이클 요약을 한 줄에 둬 헤더를 64px 예산 안에 유지한다. */}
            <div className="flex min-w-0 items-baseline gap-3">
              <h1 className="shrink-0 text-base font-semibold text-graphite">
                Fastening parameter optimizer
              </h1>
              <p className="truncate text-xs text-steel">{cycleSummary}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {headerStats.map((stat) => (
              <OverviewTile key={stat.label} {...stat} />
            ))}
          </div>
          <div className="flex shrink-0 gap-2">
            <Button disabled={loading || !data} onClick={handleOptimize} type="button" variant="secondary">
              <Wand2 size={16} />
              Optimize
            </Button>
            <Button disabled={!simulation} onClick={exportSimulation} type="button" variant="ghost">
              <Download size={16} />
              Export
            </Button>
          </div>
        </div>
      </header>

      {error && (
        <div className="shrink-0 border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mx-auto grid min-h-0 w-full max-w-[1640px] flex-1 grid-cols-1 gap-3 p-3 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <aside className="flex min-h-0 flex-col">
          <SidePanelTabs
            importPanel={
              <ImportPanel loading={loading} onImport={handleImport} onLoadSample={handleLoadSample} />
            }
            cycleSelector={
              availableCycles.length > 1 ? (
                <CycleSelector
                  cycles={availableCycles}
                  activeCycleId={activeCycleId}
                  onSelect={selectCycle}
                  excludedIds={groupSummary?.exclusion.excluded.map((entry) => entry.cycle_id)}
                />
              ) : undefined
            }
            groupOverview={
              groupSummary ? <GroupOverview summary={groupSummary} cycles={availableCycles} /> : undefined
            }
            diagnosis={
              data?.analysis.diagnosis ? <DiagnosisPanel diagnosis={data.analysis.diagnosis} /> : undefined
            }
            notes={simulation ? <SimulationNotes simulation={simulation} /> : undefined}
            excludedCount={groupSummary?.exclusion.excluded_count}
          />
        </aside>

        <section className="flex min-h-0 flex-col gap-3">
          {data && (
            <Card className="flex min-h-0 flex-1 flex-col overflow-hidden border-slate-300">
              <CardHeader className="flex shrink-0 flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <CardTitle>Waveform comparison</CardTitle>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-steel">
                    <Badge className="border-slate-200 bg-slate-50 text-steel">
                      {data.analysis.segments.method}
                    </Badge>
                    {simulation && (
                      <Badge className={confidenceTone(simulation.confidence.level)}>
                        {simulation.confidence.level} confidence
                      </Badge>
                    )}
                    {liveSimulating && (
                      <Badge className="border-blue-200 bg-blue-50 text-blue-700">
                        <Radio size={12} className="mr-1" />
                        live updating
                      </Badge>
                    )}
                    {candidateSettings && (
                      <Badge className="border-slate-200 bg-white font-mono text-slate-500">
                        {settingsSignature(candidateSettings)}
                      </Badge>
                    )}
                  </div>
                </div>
                <SegmentTimeline segments={data.analysis.segments} />
              </CardHeader>
              <CardContent className="min-h-0 flex-1 p-2">
                <WaveformChart
                  predicted={predictedWaveform}
                  segments={data.analysis.segments}
                  waveform={data.cycle.waveform}
                />
              </CardContent>
            </Card>
          )}

          {currentFeatures && (
            <Card className="shrink-0 border-slate-300">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Feature comparison</CardTitle>
                <SlidersHorizontal size={16} className="text-steel" />
              </CardHeader>
              <CardContent>
                <FeatureTable current={currentFeatures} predicted={predictedFeatures} />
              </CardContent>
            </Card>
          )}
        </section>

        <aside
          aria-label="Right control rail"
          className="flex min-h-0 flex-col gap-3 overflow-y-auto"
        >
          {currentSettings && candidateSettings && (
            <SettingsPanel
              candidate={candidateSettings}
              current={currentSettings}
              loading={loading || liveSimulating}
              onChange={updateCandidateSettings}
              onSimulate={handleSimulate}
            />
          )}

          {optimization && currentSettings && (
            <CandidateCards
              candidates={optimization.recommended}
              current={currentSettings}
              layout="rail"
              selectedLabel={selectedLabel}
              onSelect={handleSelectCandidate}
            />
          )}
        </aside>
      </div>
    </main>
  );
}
```

`Card`, `CardContent`, `CardHeader`, `CardTitle`은 여전히 쓰이므로 import를 지우지 않는다. `Button`도 헤더에서 계속 쓴다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend; node scripts/test_frontend_format.mjs`
Expected: PASS

Run: `cd frontend; npm.cmd run build`
Expected: 통과. 사용하지 않는 import가 남아 있으면 `tsc -b`가 잡아낸다.

- [ ] **Step 5: 실제 화면 확인**

Run: `cd backend; python desktop_launcher.py` 또는 `scripts/run_backend.ps1`과 `scripts/run_frontend.ps1`

1920x1080 창에서 확인한다:
- 페이지 세로 스크롤바가 없다
- 파형 차트, 설정 슬라이더, 특징 표, 추천 후보가 동시에 보인다
- 좌측 탭 3개(입력/그룹/분석)가 전환된다
- 샘플 데이터를 불러온 뒤에도 스크롤바가 생기지 않는다

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/App.tsx frontend/scripts/test_frontend_format.mjs
git commit -m "feat: fit workspace into a single viewport"
```

---

## 자체 검토 결과

**스펙 커버리지**

| 스펙 절 | 담당 태스크 |
|---|---|
| 1. 레이아웃 골격 (h-screen, min-h-0, 헤더 압축, Actions 이동) | Task 3 |
| 2. 좌측 탭 레일 (탭 3개, 배지, 내부 스크롤, 기본 탭, 복구 규칙) | Task 1 |
| 3. 중앙·우측 컬럼 | Task 3 |
| 4. 차트 가변 높이 (ResizeObserver, init/setOption 분리) | Task 2 |
| 5. 테스트 | Task 1~3 각 Step 1 |

**타입 일관성**

`sidePanelTabs`가 돌려주는 `SidePanelTab`의 필드명(`id`, `label`, `content`, `badge`, `disabled`)을 Task 1 컴포넌트가 그대로 쓴다. `SidePanelTabsProps`의 6개 prop 이름이 Task 3의 `<SidePanelTabs />` 호출과 일치한다.

**의존 순서**

Task 1과 Task 2는 서로 독립이며 각각 끝난 시점에 앱이 정상 동작한다. Task 2의 `min-h-[320px]`가 Task 3 이전의 auto 높이 부모에서 차트가 접히는 것을 막는다. Task 3은 앞의 둘을 통합한다.

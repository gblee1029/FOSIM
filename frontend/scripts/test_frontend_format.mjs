import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { candidateLabel, formatNumber, settingDelta } from "../src/lib/format.ts";
import {
  clampSettingValue,
  hasSettingChanged,
  settingRanges,
  settingsSignature,
} from "../src/lib/liveSimulation.ts";
import { selectOptimizationWaveforms } from "../src/lib/optimizationBasis.ts";
import { sidePanelTabs } from "../src/lib/sidePanelTabs.ts";
import { formatVersionTimestamp } from "../src/lib/appVersion.ts";

assert.equal(candidateLabel("quality_stable"), "Quality stable");
assert.equal(candidateLabel("cycle_time"), "Cycle time");
assert.equal(candidateLabel("minimum_change"), "Minimum change");
assert.equal(formatNumber(1.2345, "Nm", 2), "1.23 Nm");
assert.equal(settingDelta(100, 130, "ms"), "+30 ms");
assert.equal(settingDelta(820, 760, "RPM"), "-60 RPM");

const current = {
  target_speed: 820,
  target_torque: 1.2,
  clamp_rising_time: 100,
  torque_hold_time: 30,
};
assert.equal(settingsSignature(current), "820.0000|100.0000|30.0000|1.2000");
assert.equal(hasSettingChanged(current, { ...current, clamp_rising_time: 120 }), true);
assert.equal(hasSettingChanged(current, { ...current }), false);
const ranges = settingRanges(current);
assert.deepEqual(ranges.target_speed, { min: 410, max: 984, step: 10 });
assert.deepEqual(ranges.target_torque, { min: 1.14, max: 1.26, step: 0.01 });
assert.equal(clampSettingValue(999, ranges.clamp_rising_time), 250);
assert.equal(clampSettingValue(-10, ranges.torque_hold_time), 0);

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const overviewSource = readFileSync(
  new URL("../src/lib/overviewStats.ts", import.meta.url),
  "utf8",
);
const hookSource = readFileSync(
  new URL("../src/hooks/useFasteningWorkspace.ts", import.meta.url),
  "utf8",
);
const candidateSource = readFileSync(
  new URL("../src/components/CandidateCards.tsx", import.meta.url),
  "utf8",
);
const settingsSource = readFileSync(
  new URL("../src/components/SettingsPanel.tsx", import.meta.url),
  "utf8",
);
const importPanelSource = readFileSync(
  new URL("../src/components/ImportPanel.tsx", import.meta.url),
  "utf8",
);
const cycleSelectorSource = readFileSync(
  new URL("../src/components/workspace/CycleSelector.tsx", import.meta.url),
  "utf8",
);
const timelineSource = readFileSync(
  new URL("../src/components/workspace/SegmentTimeline.tsx", import.meta.url),
  "utf8",
);
const notesSource = readFileSync(
  new URL("../src/components/workspace/SimulationNotes.tsx", import.meta.url),
  "utf8",
);
const waveformSource = readFileSync(
  new URL("../src/components/WaveformChart.tsx", import.meta.url),
  "utf8",
);

assert.match(overviewSource, /buildOverviewStats/);
assert.match(overviewSource, /formatNumber/);
assert.match(overviewSource, /settingDelta/);
assert.match(appSource, /useFasteningWorkspace/);
assert.doesNotMatch(appSource, /const executeSimulation/);
assert.match(hookSource, /executeSimulation/);
assert.match(appSource, /xl:grid-cols-\[280px_minmax\(0,1fr\)_360px\]/);
assert.match(appSource, /SidePanelTabs/);
assert.match(appSource, /appVersion/);
assert.match(appSource, /Right control rail/);
// 페이지 전체가 스크롤되지 않아야 한다.
assert.match(appSource, /h-screen/);
assert.match(appSource, /overflow-hidden/);
assert.doesNotMatch(appSource, /min-h-screen/);
// Actions는 헤더로 옮겨졌으므로 우측 레일에 Actions 카드가 없다.
assert.doesNotMatch(appSource, /<CardTitle>Actions<\/CardTitle>/);
assert.match(candidateSource, /layout\?: "grid" \| "rail"/);
assert.match(settingsSource, /prediction refresh/);
assert.match(settingsSource, /Updates are recalculated automatically/);
assert.match(importPanelSource, /multiple/);
assert.match(importPanelSource, /waveformCsvs/);
assert.match(cycleSelectorSource, /CycleSelector/);
assert.match(hookSource, /activeCycleId/);
assert.match(hookSource, /selectCycle/);
assert.match(timelineSource, /SegmentTimeline/);
assert.match(notesSource, /SimulationNotes/);
assert.match(waveformSource, /ResizeObserver/);
assert.doesNotMatch(waveformSource, /h-\[520px\]/);
// init/dispose는 마운트 1회, setOption은 별도 effect여야 dataZoom 상태가 보존된다.
assert.match(waveformSource, /replaceMerge/);

const cycleA = {
  cycle: { cycle_id: "A", waveform: [{ cycle_id: "A", sample_index: 0, time_ms: 0, torque: 0.1 }] },
};
const cycleB = {
  cycle: { cycle_id: "B", waveform: [{ cycle_id: "B", sample_index: 0, time_ms: 0, torque: 0.2 }] },
};
const summaryWithExclusion = { exclusion: { included_cycle_ids: ["A"] } };

const included = selectOptimizationWaveforms([cycleA, cycleB], summaryWithExclusion);
assert.equal(included.length, 1);
assert.equal(included[0][0].cycle_id, "A");

// group_summary가 없으면 전체 사이클을 기준으로 삼는다.
assert.equal(selectOptimizationWaveforms([cycleA, cycleB], undefined).length, 2);

// 포함 목록이 비어 있으면 전체를 쓴다. 기준 집합이 공집합이면 최적화가 불가능하다.
assert.equal(
  selectOptimizationWaveforms([cycleA, cycleB], { exclusion: { included_cycle_ids: [] } }).length,
  2,
);

// 포함 목록이 어떤 사이클과도 맞지 않아도 공집합을 돌려주지 않는다.
assert.equal(
  selectOptimizationWaveforms([cycleA, cycleB], { exclusion: { included_cycle_ids: ["Z"] } }).length,
  2,
);

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

// getMonth()는 0부터 시작한다. 8월은 month=7이다.
assert.equal(formatVersionTimestamp(new Date(2026, 7, 2, 14, 30, 12)), "20260802_143012");
// 한 자리 수는 모두 zero-padding한다.
assert.equal(formatVersionTimestamp(new Date(2026, 0, 5, 9, 8, 7)), "20260105_090807");
// 자정과 연말 경계.
assert.equal(formatVersionTimestamp(new Date(2026, 11, 31, 0, 0, 0)), "20261231_000000");
assert.equal(formatVersionTimestamp(new Date(2026, 11, 31, 23, 59, 59)), "20261231_235959");

console.log("frontend format, refactor boundaries, live simulation, and layout checks passed");

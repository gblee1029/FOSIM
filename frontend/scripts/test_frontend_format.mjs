import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { candidateLabel, formatNumber, settingDelta } from "../src/lib/format.ts";
import {
  clampSettingValue,
  hasSettingChanged,
  settingRanges,
  settingsSignature,
} from "../src/lib/liveSimulation.ts";

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
const candidateSource = readFileSync(
  new URL("../src/components/CandidateCards.tsx", import.meta.url),
  "utf8",
);
const settingsSource = readFileSync(
  new URL("../src/components/SettingsPanel.tsx", import.meta.url),
  "utf8",
);

assert.match(appSource, /xl:grid-cols-\[260px_minmax\(0,1fr\)_360px\]/);
assert.match(appSource, /Station overview/);
assert.match(appSource, /Right control rail/);
assert.match(candidateSource, /layout\?: "grid" \| "rail"/);
assert.match(settingsSource, /자동으로 예상 파형을 다시 계산합니다/);

console.log("frontend format, live simulation, and layout checks passed");

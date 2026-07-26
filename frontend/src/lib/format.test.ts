import { describe, expect, it } from "vitest";

import { candidateLabel, formatNumber, settingDelta } from "./format";

describe("format helpers", () => {
  it("formats candidate labels for the operator view", () => {
    expect(candidateLabel("quality_stable")).toBe("Quality stable");
    expect(candidateLabel("cycle_time")).toBe("Cycle time");
    expect(candidateLabel("minimum_change")).toBe("Minimum change");
  });

  it("formats numeric values with units", () => {
    expect(formatNumber(1.2345, "Nm", 2)).toBe("1.23 Nm");
  });

  it("reports signed setting deltas", () => {
    expect(settingDelta(100, 130, "ms")).toBe("+30 ms");
    expect(settingDelta(820, 760, "RPM")).toBe("-60 RPM");
  });
});

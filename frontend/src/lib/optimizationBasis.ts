import type { AnalyzedCycle, GroupSummary, WaveformSample } from "../types/domain";

export function selectOptimizationWaveforms(
  cycles: AnalyzedCycle[],
  summary: GroupSummary | undefined,
): WaveformSample[][] {
  const includedIds = new Set(summary?.exclusion?.included_cycle_ids ?? []);
  const filtered =
    includedIds.size === 0
      ? cycles
      : cycles.filter((entry) => includedIds.has(entry.cycle.cycle_id));
  const basis = filtered.length > 0 ? filtered : cycles;
  return basis.map((entry) => entry.cycle.waveform);
}

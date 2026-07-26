export function candidateLabel(label: string): string {
  const labels: Record<string, string> = {
    quality_stable: "Quality stable",
    cycle_time: "Cycle time",
    minimum_change: "Minimum change",
  };
  return labels[label] ?? label.replaceAll("_", " ");
}

export function formatNumber(value: number | null | undefined, unit = "", digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const formatted = value.toLocaleString("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
  return unit ? `${formatted} ${unit}` : formatted;
}

export function settingDelta(current: number, candidate: number, unit = ""): string {
  const delta = candidate - current;
  const sign = delta > 0 ? "+" : "";
  const rounded = Number.isInteger(delta) ? delta.toFixed(0) : delta.toFixed(2);
  return unit ? `${sign}${rounded} ${unit}` : `${sign}${rounded}`;
}

export function confidenceTone(level: string): string {
  if (level === "high") return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (level === "medium") return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-red-700 bg-red-50 border-red-200";
}

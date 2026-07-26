import { Gauge, Target, Timer, TrendingUp, type LucideIcon } from "lucide-react";

import type { FeatureMap } from "../types/domain";
import { formatNumber, settingDelta } from "./format";

export type OverviewStat = {
  label: string;
  value: string;
  delta: string;
  icon: LucideIcon;
  accent: string;
};

const overviewConfig: Array<{
  label: string;
  key: string;
  unit: string;
  digits: number;
  icon: LucideIcon;
  accent: string;
}> = [
  { label: "Final", key: "final_torque", unit: "Nm", digits: 3, icon: Target, accent: "border-l-torque" },
  {
    label: "Overshoot",
    key: "overshoot_percent",
    unit: "%",
    digits: 2,
    icon: TrendingUp,
    accent: "border-l-amber-500",
  },
  { label: "Clamp", key: "clamp_time", unit: "ms", digits: 0, icon: Timer, accent: "border-l-speed" },
  {
    label: "Stability",
    key: "waveform_stability_score",
    unit: "",
    digits: 2,
    icon: Gauge,
    accent: "border-l-angle",
  },
];

export function buildOverviewStats(current?: FeatureMap, predicted?: FeatureMap): OverviewStat[] {
  return overviewConfig.map((item) => {
    const currentValue = current?.[item.key];
    const predictedValue = predicted?.[item.key];
    return {
      label: item.label,
      value: formatNumber(predictedValue ?? currentValue, item.unit, item.digits),
      delta:
        currentValue !== undefined && predictedValue !== undefined
          ? settingDelta(currentValue, predictedValue, item.unit)
          : "current",
      icon: item.icon,
      accent: item.accent,
    };
  });
}

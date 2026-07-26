import type { FeatureMap } from "../types/domain";
import { formatNumber } from "../lib/format";

type Props = {
  current: FeatureMap;
  predicted?: FeatureMap;
};

const rows: Array<[keyof FeatureMap, string, string, number]> = [
  ["final_torque", "Final torque", "Nm", 3],
  ["peak_torque", "Peak torque", "Nm", 3],
  ["overshoot_percent", "Overshoot", "%", 2],
  ["clamp_time", "Clamp time", "ms", 1],
  ["clamp_gradient", "Clamp gradient", "Nm/ms", 5],
  ["hold_std", "Hold std", "Nm", 4],
  ["total_time", "Fastening time", "ms", 1],
  ["waveform_stability_score", "Stability", "", 2],
];

export function FeatureTable({ current, predicted }: Props) {
  return (
    <div className="overflow-hidden rounded-md border border-slate-200">
      <table className="w-full text-left text-xs">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Metric</th>
            <th className="px-3 py-2 font-medium">Current</th>
            <th className="px-3 py-2 font-medium">Predicted</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map(([key, label, unit, digits]) => (
            <tr key={String(key)}>
              <td className="px-3 py-2 text-steel">{label}</td>
              <td className="px-3 py-2 font-mono text-graphite">
                {formatNumber(current[key], unit, digits)}
              </td>
              <td className="px-3 py-2 font-mono text-graphite">
                {predicted ? formatNumber(predicted[key], unit, digits) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

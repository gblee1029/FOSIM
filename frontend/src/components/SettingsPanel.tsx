import { Play } from "lucide-react";

import { settingDelta } from "../lib/format";
import { clampSettingValue, settingRanges } from "../lib/liveSimulation";
import type { FasteningSettings } from "../types/domain";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";

type Props = {
  current: FasteningSettings;
  candidate: FasteningSettings;
  onChange: (settings: FasteningSettings) => void;
  onSimulate: () => void;
  loading: boolean;
};

type LiveSettingKey = "target_speed" | "clamp_rising_time" | "torque_hold_time" | "target_torque";

const fields: Array<[LiveSettingKey, string, string]> = [
  ["target_speed", "Target Speed", "RPM"],
  ["clamp_rising_time", "Clamp Rising Time", "ms"],
  ["torque_hold_time", "Torque Hold Time", "ms"],
  ["target_torque", "Target Torque", "Nm"],
];

export function SettingsPanel({ current, candidate, onChange, onSimulate, loading }: Props) {
  const ranges = settingRanges(current);
  const updateSetting = (key: LiveSettingKey, value: number) => {
    const range = ranges[key];
    onChange({
      ...candidate,
      [key]: range ? clampSettingValue(value, range) : value,
    });
  };

  return (
    <Card className="border-slate-300">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>Live setting editor</CardTitle>
            <p className="mt-1 text-xs text-steel">Adjust a value and watch the prediction refresh.</p>
          </div>
          <span className="rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700">
            Auto
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {fields.map(([key, label, unit]) => (
          <div key={key} className="space-y-2 rounded-md border border-slate-100 bg-white p-3">
            <div className="grid grid-cols-[1fr_92px_42px] items-center gap-2">
              <label className="text-xs font-medium text-steel" htmlFor={key}>
                {label}
              </label>
              <Input
                id={key}
                type="number"
                step={ranges[key].step}
                value={candidate[key] ?? ""}
                onChange={(event) => updateSetting(key, Number(event.target.value))}
              />
              <span className="text-xs text-slate-500">{unit}</span>
            </div>
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span className="text-slate-400">base {current[key] ?? "-"}</span>
              <span className="text-graphite">
                {settingDelta(Number(current[key] ?? 0), Number(candidate[key] ?? 0), unit)}
              </span>
            </div>
            <input
              aria-label={`${label} slider`}
              className="h-2 w-full cursor-pointer accent-torque"
              max={ranges[key].max}
              min={ranges[key].min}
              step={ranges[key].step}
              type="range"
              value={Number(candidate[key] ?? current[key] ?? ranges[key].min)}
              onChange={(event) => updateSetting(key, Number(event.target.value))}
            />
            <div className="flex justify-between font-mono text-[10px] text-slate-400">
              <span>{ranges[key].min}</span>
              <span>{ranges[key].max}</span>
            </div>
          </div>
        ))}
        <p className="text-xs leading-5 text-steel">
          Updates are recalculated automatically after each adjustment. Use the button when you want an immediate
          refresh.
        </p>
        <Button className="w-full" disabled={loading} onClick={onSimulate} type="button">
          <Play size={16} />
          Recalculate now
        </Button>
      </CardContent>
    </Card>
  );
}

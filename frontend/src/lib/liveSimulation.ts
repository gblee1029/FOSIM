import type { FasteningSettings } from "../types/domain";

export type SettingRange = {
  min: number;
  max: number;
  step: number;
};

export type SettingRangeMap = Record<keyof Pick<
  FasteningSettings,
  "target_speed" | "clamp_rising_time" | "torque_hold_time" | "target_torque"
>, SettingRange>;

export function settingsSignature(settings: FasteningSettings): string {
  return [
    settings.target_speed,
    settings.clamp_rising_time,
    settings.torque_hold_time,
    settings.target_torque,
  ]
    .map((value) => Number(value).toFixed(4))
    .join("|");
}

export function hasSettingChanged(
  current: FasteningSettings,
  candidate: FasteningSettings,
): boolean {
  return settingsSignature(current) !== settingsSignature(candidate);
}

export function settingRanges(current: FasteningSettings): SettingRangeMap {
  return {
    target_speed: {
      min: Math.max(50, Math.round(current.target_speed * 0.5)),
      max: Math.max(100, Math.round(current.target_speed * 1.2)),
      step: 10,
    },
    clamp_rising_time: {
      min: 20,
      max: 250,
      step: 5,
    },
    torque_hold_time: {
      min: 0,
      max: 150,
      step: 5,
    },
    target_torque: {
      min: roundTo(current.target_torque * 0.95, 0.01),
      max: roundTo(current.target_torque * 1.05, 0.01),
      step: 0.01,
    },
  };
}

export function clampSettingValue(value: number, range: SettingRange): number {
  return Math.min(range.max, Math.max(range.min, value));
}

function roundTo(value: number, step: number): number {
  const decimals = step.toString().split(".")[1]?.length ?? 0;
  return Number((Math.round(value / step) * step).toFixed(decimals));
}

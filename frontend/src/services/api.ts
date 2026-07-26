import type {
  FasteningSettings,
  ImportResponse,
  OptimizationResult,
  SimulationResult,
  WaveformSample,
} from "../types/domain";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function loadSampleCycle(): Promise<ImportResponse> {
  return request<ImportResponse>("/sample/cycle");
}

export function importCsv(settingsCsv: string, waveformCsv: string): Promise<ImportResponse> {
  return request<ImportResponse>("/import/csv", {
    method: "POST",
    body: JSON.stringify({ settings_csv: settingsCsv, waveform_csv: waveformCsv }),
  });
}

export function runSimulation(
  waveform: WaveformSample[],
  currentSettings: FasteningSettings,
  candidateSettings: FasteningSettings,
): Promise<SimulationResult> {
  return request<SimulationResult>("/simulations", {
    method: "POST",
    body: JSON.stringify({
      waveform,
      current_settings: currentSettings,
      candidate_settings: candidateSettings,
    }),
  });
}

export function runOptimization(
  waveform: WaveformSample[],
  currentSettings: FasteningSettings,
): Promise<OptimizationResult> {
  const target = currentSettings.target_torque;
  return request<OptimizationResult>("/optimizations", {
    method: "POST",
    body: JSON.stringify({
      waveform,
      current_settings: currentSettings,
      objectives: {
        target_torque_min: target * 0.97,
        target_torque_max: target * 1.03,
        max_overshoot_percent: 6,
        max_fastening_time: 720,
        min_stability_score: 0.62,
        allow_target_torque_change: false,
      },
    }),
  });
}

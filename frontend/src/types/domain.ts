export type FasteningSettings = {
  target_speed: number;
  target_torque: number;
  clamp_rising_time: number;
  torque_hold_time: number;
  seating_sensitivity?: number | null;
  speed_adjust_time?: number | null;
};

export type WaveformSample = {
  cycle_id: string;
  sample_index: number;
  time_ms: number;
  torque: number;
  speed?: number;
  angle?: number;
  current?: number;
  event_code?: string;
};

export type Segments = {
  start_time: number;
  free_run_end_time: number;
  engage_start_time: number;
  seating_time: number;
  target_reach_time: number;
  hold_end_time: number;
  stop_time: number;
  confidence: number;
  method: string;
  warnings: string[];
};

export type FeatureMap = Record<string, number>;

export type Diagnosis = {
  anomaly_type: string;
  severity: string;
  confidence: number;
  evidence_features: string[];
  related_parameters: string[];
  recommended_checks: string[];
  description: string;
};

export type ImportedCycle = {
  cycle_id: string;
  settings: FasteningSettings;
  waveform: WaveformSample[];
  metadata: Record<string, unknown>;
  issues: Array<{ field: string; message: string; severity: string }>;
};

export type Analysis = {
  segments: Segments;
  features: FeatureMap;
  diagnosis: Diagnosis;
};

export type ImportResponse = {
  cycle: ImportedCycle;
  analysis: Analysis;
};

export type SimulationResult = {
  simulation_type: string;
  source_cycle_id: string;
  current_settings: FasteningSettings;
  candidate_settings: FasteningSettings;
  setting_changes: Record<string, number>;
  current_features: FeatureMap;
  predicted_features: FeatureMap;
  confidence: {
    level: string;
    score: number;
    factors: string[];
  };
  warnings: string[];
  predicted_waveform: WaveformSample[];
};

export type CandidateEvaluation = {
  label: string;
  settings: FasteningSettings;
  score: number;
  score_breakdown: Record<string, number>;
  simulation: SimulationResult;
  reason: string;
  warnings: string[];
};

export type OptimizationResult = {
  evaluated_count: number;
  rejected_count: number;
  recommended: CandidateEvaluation[];
  all_candidates: CandidateEvaluation[];
};

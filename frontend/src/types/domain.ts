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

export type AnalyzedCycle = {
  cycle: ImportedCycle;
  analysis: Analysis;
};

export type SettingsGroupInfo = {
  key: number[];
  settings: FasteningSettings;
  cycle_ids: string[];
  cycle_count: number;
};

export type FeatureDistribution = {
  feature: string;
  mean: number;
  std: number;
  min: number;
  max: number;
  p05: number;
  p95: number;
  count: number;
};

export type ExclusionEntry = {
  cycle_id: string;
  reason: string;
  detail: string;
};

export type ExclusionInfo = {
  included_cycle_ids: string[];
  included_count: number;
  excluded: ExclusionEntry[];
  excluded_count: number;
  warnings: string[];
};

export type WaveformEnvelope = {
  time_ms: number[];
  torque_min: number[];
  torque_max: number[];
  torque_median: number[];
};

export type GroupSummary = {
  groups: SettingsGroupInfo[];
  is_single_group: boolean;
  active_group_index: number;
  distributions: Record<string, FeatureDistribution>;
  capability: Record<string, number>;
  envelope: WaveformEnvelope;
  exclusion: ExclusionInfo;
  confidence_grade: string;
};

export type ImportResponse = AnalyzedCycle & {
  cycles?: AnalyzedCycle[];
  active_cycle_id?: string;
  group_summary?: GroupSummary;
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

export type CycleEvaluation = {
  cycle_id: string;
  simulation: SimulationResult;
  violations: string[];
};

export type CandidateEvaluation = {
  label: string;
  settings: FasteningSettings;
  score: number;
  score_breakdown: Record<string, number>;
  simulation: SimulationResult;
  reason: string;
  warnings: string[];
  per_cycle: CycleEvaluation[];
  cycle_count: number;
  gate_mode: string;
  confidence_grade: string;
};

export type OptimizationResult = {
  evaluated_count: number;
  rejected_count: number;
  recommended: CandidateEvaluation[];
  all_candidates: CandidateEvaluation[];
  rejection_details: Array<{ settings: FasteningSettings; cycle_id: string; violation: string }>;
  cycle_count: number;
  gate_mode: string;
  confidence_grade: string;
};

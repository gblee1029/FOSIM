import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { buildOverviewStats } from "../lib/overviewStats";
import { hasSettingChanged, settingsSignature } from "../lib/liveSimulation";
import { importCsv, loadSampleCycle, runOptimization, runSimulation } from "../services/api";
import type {
  CandidateEvaluation,
  FasteningSettings,
  ImportResponse,
  OptimizationResult,
  SimulationResult,
} from "../types/domain";

function sampleCandidateFrom(settings: FasteningSettings): FasteningSettings {
  return {
    ...settings,
    target_speed: settings.target_speed - 60,
    clamp_rising_time: settings.clamp_rising_time + 40,
    torque_hold_time: settings.torque_hold_time + 20,
  };
}

function cycleSummaryFrom(data: ImportResponse | null): string {
  if (!data) return "Sample data is loading";
  const product = String(data.cycle.metadata.product_model ?? "Model");
  const process = String(data.cycle.metadata.process_id ?? "Process");
  const position = String(data.cycle.metadata.screw_position ?? "Position");
  return `${data.cycle.cycle_id} / ${product} / ${process} / ${position}`;
}

export function useFasteningWorkspace() {
  const [data, setData] = useState<ImportResponse | null>(null);
  const [candidateSettings, setCandidateSettings] = useState<FasteningSettings | null>(null);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [optimization, setOptimization] = useState<OptimizationResult | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [liveSimulating, setLiveSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const liveRequestId = useRef(0);
  const latestCandidateSignature = useRef("");

  const currentSettings = data?.cycle.settings;
  const predictedWaveform = simulation?.predicted_waveform;
  const currentFeatures = data?.analysis.features;
  const predictedFeatures = simulation?.predicted_features;

  const executeSimulation = useCallback(
    async (mode: "manual" | "live") => {
      if (!data || !candidateSettings) return;
      const requestId = ++liveRequestId.current;
      const candidateSignature = settingsSignature(candidateSettings);
      latestCandidateSignature.current = candidateSignature;
      if (mode === "manual") {
        setLoading(true);
      } else {
        setLiveSimulating(true);
      }
      setError(null);
      try {
        const response = await runSimulation(data.cycle.waveform, data.cycle.settings, candidateSettings);
        if (requestId === liveRequestId.current && candidateSignature === latestCandidateSignature.current) {
          setSimulation(response);
          setSelectedLabel(undefined);
        }
      } catch (err) {
        if (requestId === liveRequestId.current) {
          setError(err instanceof Error ? err.message : "Simulation failed.");
        }
      } finally {
        if (requestId === liveRequestId.current) {
          if (mode === "manual") {
            setLoading(false);
          } else {
            setLiveSimulating(false);
          }
        }
      }
    },
    [candidateSettings, data],
  );

  const handleLoadSample = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await loadSampleCycle();
      setData(response);
      setCandidateSettings(sampleCandidateFrom(response.cycle.settings));
      setSimulation(null);
      setOptimization(null);
      setSelectedLabel(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load sample cycle.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void handleLoadSample();
  }, [handleLoadSample]);

  useEffect(() => {
    if (!data || !candidateSettings) return;
    latestCandidateSignature.current = settingsSignature(candidateSettings);
    if (!hasSettingChanged(data.cycle.settings, candidateSettings)) {
      liveRequestId.current += 1;
      setSimulation(null);
      setLiveSimulating(false);
      return;
    }
    const timer = window.setTimeout(() => {
      void executeSimulation("live");
    }, 350);
    return () => window.clearTimeout(timer);
  }, [candidateSettings, data, executeSimulation]);

  async function handleImport(settingsCsv: string, waveformCsv: string) {
    if (!settingsCsv || !waveformCsv) {
      setError("Select both settings and waveform CSV files.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await importCsv(settingsCsv, waveformCsv);
      setData(response);
      setCandidateSettings(response.cycle.settings);
      setSimulation(null);
      setOptimization(null);
      setSelectedLabel(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV import failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSimulate() {
    await executeSimulation("manual");
  }

  async function handleOptimize() {
    if (!data) return;
    setLoading(true);
    setError(null);
    try {
      const response = await runOptimization(data.cycle.waveform, data.cycle.settings);
      setOptimization(response);
      const first = response.recommended[0];
      if (first) {
        setSimulation(first.simulation);
        setCandidateSettings(first.settings);
        setSelectedLabel(first.label);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimization failed.");
    } finally {
      setLoading(false);
    }
  }

  function handleSelectCandidate(candidate: CandidateEvaluation) {
    setSimulation(candidate.simulation);
    setCandidateSettings(candidate.settings);
    setSelectedLabel(candidate.label);
  }

  function updateCandidateSettings(settings: FasteningSettings) {
    setCandidateSettings(settings);
  }

  function exportSimulation() {
    if (!simulation) return;
    const blob = new Blob([JSON.stringify(simulation, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${simulation.source_cycle_id || "cycle"}-simulation.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const headerStats = useMemo(
    () => buildOverviewStats(currentFeatures, predictedFeatures),
    [currentFeatures, predictedFeatures],
  );
  const cycleSummary = useMemo(() => cycleSummaryFrom(data), [data]);

  return {
    data,
    candidateSettings,
    simulation,
    optimization,
    selectedLabel,
    loading,
    liveSimulating,
    error,
    currentSettings,
    predictedWaveform,
    currentFeatures,
    predictedFeatures,
    headerStats,
    cycleSummary,
    handleLoadSample,
    handleImport,
    handleSimulate,
    handleOptimize,
    handleSelectCandidate,
    updateCandidateSettings,
    exportSimulation,
  };
}

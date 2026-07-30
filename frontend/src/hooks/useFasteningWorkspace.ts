import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { buildOverviewStats } from "../lib/overviewStats";
import { hasSettingChanged, settingsSignature } from "../lib/liveSimulation";
import { selectOptimizationWaveforms } from "../lib/optimizationBasis";
import { importCsv, loadSampleCycle, runOptimization, runSimulation } from "../services/api";
import type {
  AnalyzedCycle,
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

function cyclesFrom(response: ImportResponse | null): AnalyzedCycle[] {
  if (!response) return [];
  return response.cycles?.length ? response.cycles : [{ cycle: response.cycle, analysis: response.analysis }];
}

function cycleSummaryFrom(entry: AnalyzedCycle | undefined): string {
  if (!entry) return "Sample data is loading";
  const product = String(entry.cycle.metadata.product_model ?? "Model");
  const process = String(entry.cycle.metadata.process_id ?? "Process");
  const position = String(entry.cycle.metadata.screw_position ?? "Position");
  return `${entry.cycle.cycle_id} / ${product} / ${process} / ${position}`;
}

export function useFasteningWorkspace() {
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);
  const [activeCycleId, setActiveCycleId] = useState<string | undefined>();
  const [candidateSettings, setCandidateSettings] = useState<FasteningSettings | null>(null);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [optimization, setOptimization] = useState<OptimizationResult | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [liveSimulating, setLiveSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const liveRequestId = useRef(0);
  const latestCandidateSignature = useRef("");

  const availableCycles = useMemo(() => cyclesFrom(importResult), [importResult]);
  const activeEntry = useMemo(() => {
    if (!availableCycles.length) return undefined;
    return availableCycles.find((entry) => entry.cycle.cycle_id === activeCycleId) ?? availableCycles[0];
  }, [activeCycleId, availableCycles]);

  const data = useMemo<ImportResponse | null>(() => {
    if (!activeEntry) return null;
    return {
      ...activeEntry,
      cycles: availableCycles,
      active_cycle_id: activeEntry.cycle.cycle_id,
    };
  }, [activeEntry, availableCycles]);

  const currentSettings = activeEntry?.cycle.settings;
  const predictedWaveform = simulation?.predicted_waveform;
  const currentFeatures = activeEntry?.analysis.features;
  const predictedFeatures = simulation?.predicted_features;

  const resetDerivedState = useCallback(() => {
    setSimulation(null);
    setOptimization(null);
    setSelectedLabel(undefined);
  }, []);

  const executeSimulation = useCallback(
    async (mode: "manual" | "live") => {
      if (!activeEntry || !candidateSettings) return;
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
        const response = await runSimulation(activeEntry.cycle.waveform, activeEntry.cycle.settings, candidateSettings);
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
    [activeEntry, candidateSettings],
  );

  const handleLoadSample = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await loadSampleCycle();
      const cycles = cyclesFrom(response);
      const first = cycles[0];
      setImportResult(response);
      setActiveCycleId(first?.cycle.cycle_id);
      setCandidateSettings(first ? sampleCandidateFrom(first.cycle.settings) : null);
      resetDerivedState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load sample cycle.");
    } finally {
      setLoading(false);
    }
  }, [resetDerivedState]);

  useEffect(() => {
    void handleLoadSample();
  }, [handleLoadSample]);

  useEffect(() => {
    if (!activeEntry || !candidateSettings) return;
    latestCandidateSignature.current = settingsSignature(candidateSettings);
    if (!hasSettingChanged(activeEntry.cycle.settings, candidateSettings)) {
      liveRequestId.current += 1;
      setSimulation(null);
      setLiveSimulating(false);
      return;
    }
    const timer = window.setTimeout(() => {
      void executeSimulation("live");
    }, 350);
    return () => window.clearTimeout(timer);
  }, [activeEntry, candidateSettings, executeSimulation]);

  async function handleImport(settingsCsv: string, waveformCsvs: string[]) {
    if (!settingsCsv || !waveformCsvs.length) {
      setError("Select settings CSV and at least one waveform CSV file.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await importCsv(settingsCsv, waveformCsvs);
      const cycles = cyclesFrom(response);
      const first = cycles[0];
      setImportResult(response);
      setActiveCycleId(first?.cycle.cycle_id);
      setCandidateSettings(first?.cycle.settings ?? null);
      resetDerivedState();
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
    if (!activeEntry) return;
    setLoading(true);
    setError(null);
    try {
      const optimizationWaveforms = selectOptimizationWaveforms(
        availableCycles,
        importResult?.group_summary,
      );
      const response = await runOptimization(optimizationWaveforms, activeEntry.cycle.settings);
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

  function selectCycle(cycleId: string) {
    const next = availableCycles.find((entry) => entry.cycle.cycle_id === cycleId);
    if (!next) return;
    liveRequestId.current += 1;
    setActiveCycleId(cycleId);
    setCandidateSettings(next.cycle.settings);
    setError(null);
    resetDerivedState();
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
  const cycleSummary = useMemo(() => cycleSummaryFrom(activeEntry), [activeEntry]);

  return {
    data,
    availableCycles,
    activeCycleId: activeEntry?.cycle.cycle_id,
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
    selectCycle,
    updateCandidateSettings,
    exportSimulation,
  };
}

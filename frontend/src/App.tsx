import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Download,
  Gauge,
  Radio,
  SlidersHorizontal,
  Target,
  Timer,
  TrendingUp,
  Wand2,
} from "lucide-react";

import { CandidateCards } from "./components/CandidateCards";
import { DiagnosisPanel } from "./components/DiagnosisPanel";
import { FeatureTable } from "./components/FeatureTable";
import { ImportPanel } from "./components/ImportPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { WaveformChart } from "./components/WaveformChart";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { confidenceTone, formatNumber, settingDelta } from "./lib/format";
import { hasSettingChanged, settingsSignature } from "./lib/liveSimulation";
import { importCsv, loadSampleCycle, runOptimization, runSimulation } from "./services/api";
import type {
  CandidateEvaluation,
  FasteningSettings,
  FeatureMap,
  ImportResponse,
  OptimizationResult,
  Segments,
  SimulationResult,
} from "./types/domain";

function App() {
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

  useEffect(() => {
    void handleLoadSample();
  }, []);

  const executeSimulation = useCallback(
    async (mode: "manual" | "live") => {
      if (!data || !candidateSettings) return;
      const requestId = ++liveRequestId.current;
      const candidateSignature = settingsSignature(candidateSettings);
      if (mode === "manual") {
        setLoading(true);
      } else {
        setLiveSimulating(true);
      }
      setError(null);
      try {
        const response = await runSimulation(
          data.cycle.waveform,
          data.cycle.settings,
          candidateSettings,
        );
        if (
          requestId === liveRequestId.current &&
          candidateSignature === latestCandidateSignature.current
        ) {
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

  const headerStats = useMemo(
    () => buildOverviewStats(currentFeatures, predictedFeatures),
    [currentFeatures, predictedFeatures],
  );

  const cycleSummary = useMemo(() => {
    if (!data) return "Sample data is loading";
    const product = String(data.cycle.metadata.product_model ?? "Model");
    const process = String(data.cycle.metadata.process_id ?? "Process");
    const position = String(data.cycle.metadata.screw_position ?? "Position");
    return `${data.cycle.cycle_id} / ${product} / ${process} / ${position}`;
  }, [data]);

  async function handleLoadSample() {
    setLoading(true);
    setError(null);
    try {
      const response = await loadSampleCycle();
      setData(response);
      setCandidateSettings({
        ...response.cycle.settings,
        target_speed: response.cycle.settings.target_speed - 60,
        clamp_rising_time: response.cycle.settings.clamp_rising_time + 40,
        torque_hold_time: response.cycle.settings.torque_hold_time + 20,
      });
      setSimulation(null);
      setOptimization(null);
      setSelectedLabel(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load sample cycle.");
    } finally {
      setLoading(false);
    }
  }

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

  return (
    <main className="min-h-screen bg-[#eef1ed] text-graphite">
      <header className="sticky top-0 z-20 border-b border-slate-300 bg-[#f8faf6]/95 backdrop-blur">
        <div className="mx-auto grid max-w-[1640px] gap-4 px-4 py-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-steel">
              <Activity size={15} />
              SH-2 Smart Manager MVP
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal text-graphite">
              Fastening parameter optimizer
            </h1>
            <p className="mt-1 truncate text-sm text-steel">{cycleSummary}</p>
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {headerStats.map((stat) => (
              <OverviewTile key={stat.label} {...stat} />
            ))}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1640px] px-4 py-4">
        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[260px_minmax(0,1fr)_360px]">
          <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Station overview
            </div>
            <ImportPanel loading={loading} onImport={handleImport} onLoadSample={handleLoadSample} />
            {data?.analysis.diagnosis && <DiagnosisPanel diagnosis={data.analysis.diagnosis} />}
            {simulation && <SimulationNotes simulation={simulation} />}
          </aside>

          <section className="min-w-0 space-y-4">
            {data && (
              <Card className="overflow-hidden border-slate-300">
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <CardTitle>Waveform comparison</CardTitle>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-steel">
                      <Badge className="border-slate-200 bg-slate-50 text-steel">
                        {data.analysis.segments.method}
                      </Badge>
                      {simulation && (
                        <Badge className={confidenceTone(simulation.confidence.level)}>
                          {simulation.confidence.level} confidence
                        </Badge>
                      )}
                      {liveSimulating && (
                        <Badge className="border-blue-200 bg-blue-50 text-blue-700">
                          <Radio size={12} className="mr-1" />
                          live updating
                        </Badge>
                      )}
                      {candidateSettings && (
                        <Badge className="border-slate-200 bg-white font-mono text-slate-500">
                          {settingsSignature(candidateSettings)}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <SegmentTimeline segments={data.analysis.segments} />
                </CardHeader>
                <CardContent className="p-2 md:p-4">
                  <WaveformChart
                    predicted={predictedWaveform}
                    segments={data.analysis.segments}
                    waveform={data.cycle.waveform}
                  />
                </CardContent>
              </Card>
            )}

            {currentFeatures && (
              <Card className="border-slate-300">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Feature comparison</CardTitle>
                  <SlidersHorizontal size={16} className="text-steel" />
                </CardHeader>
                <CardContent>
                  <FeatureTable current={currentFeatures} predicted={predictedFeatures} />
                </CardContent>
              </Card>
            )}
          </section>

          <aside aria-label="Right control rail" className="space-y-4 xl:sticky xl:top-24 xl:self-start">
            {currentSettings && candidateSettings && (
              <SettingsPanel
                candidate={candidateSettings}
                current={currentSettings}
                loading={loading || liveSimulating}
                onChange={setCandidateSettings}
                onSimulate={handleSimulate}
              />
            )}

            <Card className="border-slate-300">
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-2">
                <Button disabled={loading || !data} onClick={handleOptimize} type="button" variant="secondary">
                  <Wand2 size={16} />
                  Optimize
                </Button>
                <Button disabled={!simulation} onClick={exportSimulation} type="button" variant="ghost">
                  <Download size={16} />
                  Export
                </Button>
              </CardContent>
            </Card>

            {optimization && currentSettings && (
              <CandidateCards
                candidates={optimization.recommended}
                current={currentSettings}
                layout="rail"
                selectedLabel={selectedLabel}
                onSelect={handleSelectCandidate}
              />
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}

type OverviewTileProps = {
  label: string;
  value: string;
  delta: string;
  icon: typeof Target;
  accent: string;
};

function OverviewTile({ label, value, delta, icon: Icon, accent }: OverviewTileProps) {
  return (
    <div className={`min-w-32 rounded-md border border-slate-200 border-l-4 bg-white px-3 py-2 ${accent}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</div>
        <Icon size={14} className="text-slate-400" />
      </div>
      <div className="mt-1 font-mono text-sm text-graphite">{value}</div>
      <div className="font-mono text-[11px] text-steel">{delta}</div>
    </div>
  );
}

function SegmentTimeline({ segments }: { segments: Segments }) {
  const items: Array<[keyof Segments, string]> = [
    ["engage_start_time", "Engage"],
    ["seating_time", "Seat"],
    ["target_reach_time", "Target"],
    ["hold_end_time", "Hold"],
    ["stop_time", "Stop"],
  ];
  const start = segments.start_time;
  const span = Math.max(segments.stop_time - start, 1);

  return (
    <div className="w-full max-w-md rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="relative h-8">
        <div className="absolute left-0 right-0 top-4 h-px bg-slate-300" />
        {items.map(([key, label]) => {
          const value = Number(segments[key] ?? start);
          const left = Math.max(0, Math.min(100, ((value - start) / span) * 100));
          return (
            <div key={key} className="absolute top-0 -translate-x-1/2" style={{ left: `${left}%` }}>
              <div className="mx-auto h-3 w-3 rounded-full border border-white bg-graphite shadow-sm" />
              <div className="mt-1 whitespace-nowrap text-[10px] font-medium text-steel">{label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SimulationNotes({ simulation }: { simulation: SimulationResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Simulation notes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <NoteList title="Confidence factors" items={simulation.confidence.factors} />
        <NoteList
          title="Warnings"
          items={simulation.warnings.length ? simulation.warnings : ["No MVP warning."]}
        />
      </CardContent>
    </Card>
  );
}

function NoteList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</div>
      <ul className="space-y-1 text-steel">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function buildOverviewStats(current?: FeatureMap, predicted?: FeatureMap): OverviewTileProps[] {
  const config: Array<{
    label: string;
    key: string;
    unit: string;
    digits: number;
    icon: typeof Target;
    accent: string;
  }> = [
    { label: "Final", key: "final_torque", unit: "Nm", digits: 3, icon: Target, accent: "border-l-torque" },
    { label: "Overshoot", key: "overshoot_percent", unit: "%", digits: 2, icon: TrendingUp, accent: "border-l-amber-500" },
    { label: "Clamp", key: "clamp_time", unit: "ms", digits: 0, icon: Timer, accent: "border-l-speed" },
    { label: "Stability", key: "waveform_stability_score", unit: "", digits: 2, icon: Gauge, accent: "border-l-angle" },
  ];

  return config.map((item) => {
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

export default App;

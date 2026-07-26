import { Activity, Download, Radio, SlidersHorizontal, Wand2 } from "lucide-react";

import { CandidateCards } from "./components/CandidateCards";
import { DiagnosisPanel } from "./components/DiagnosisPanel";
import { FeatureTable } from "./components/FeatureTable";
import { ImportPanel } from "./components/ImportPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { WaveformChart } from "./components/WaveformChart";
import { CycleSelector } from "./components/workspace/CycleSelector";
import { OverviewTile } from "./components/workspace/OverviewTile";
import { SegmentTimeline } from "./components/workspace/SegmentTimeline";
import { SimulationNotes } from "./components/workspace/SimulationNotes";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { useFasteningWorkspace } from "./hooks/useFasteningWorkspace";
import { confidenceTone } from "./lib/format";
import { settingsSignature } from "./lib/liveSimulation";

function App() {
  const {
    data,
    availableCycles,
    activeCycleId,
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
  } = useFasteningWorkspace();

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
            {availableCycles.length > 1 && (
              <CycleSelector cycles={availableCycles} activeCycleId={activeCycleId} onSelect={selectCycle} />
            )}
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
                onChange={updateCandidateSettings}
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

export default App;

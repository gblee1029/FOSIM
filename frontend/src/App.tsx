import { Activity, Download, Radio, SlidersHorizontal, Wand2 } from "lucide-react";

import { CandidateCards } from "./components/CandidateCards";
import { DiagnosisPanel } from "./components/DiagnosisPanel";
import { FeatureTable } from "./components/FeatureTable";
import { ImportPanel } from "./components/ImportPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { WaveformChart } from "./components/WaveformChart";
import { CycleSelector } from "./components/workspace/CycleSelector";
import { GroupOverview } from "./components/workspace/GroupOverview";
import { OverviewTile } from "./components/workspace/OverviewTile";
import { SegmentTimeline } from "./components/workspace/SegmentTimeline";
import { SidePanelTabs } from "./components/workspace/SidePanelTabs";
import { SimulationNotes } from "./components/workspace/SimulationNotes";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { useFasteningWorkspace } from "./hooks/useFasteningWorkspace";
import { appVersion } from "./lib/appVersion";
import { confidenceTone } from "./lib/format";
import { settingsSignature } from "./lib/liveSimulation";

function App() {
  const {
    data,
    availableCycles,
    groupSummary,
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
    <main className="flex h-screen flex-col overflow-hidden bg-[#eef1ed] text-graphite">
      <header className="shrink-0 border-b border-slate-300 bg-[#f8faf6]">
        <div className="mx-auto flex max-w-[1640px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-steel">
              <Activity size={14} />
              SH-2 Smart Manager MVP
            </div>
            {/* 제목과 사이클 요약을 한 줄에 둬 헤더를 64px 예산 안에 유지한다. */}
            <div className="flex min-w-0 items-baseline gap-3">
              <h1 className="shrink-0 text-base font-semibold text-graphite">
                Fastening parameter optimizer
              </h1>
              <span className="shrink-0 font-mono text-[11px] text-slate-400">{appVersion}</span>
              <p className="truncate text-xs text-steel">{cycleSummary}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {headerStats.map((stat) => (
              <OverviewTile key={stat.label} {...stat} />
            ))}
          </div>
          <div className="flex shrink-0 gap-2">
            <Button disabled={loading || !data} onClick={handleOptimize} type="button" variant="secondary">
              <Wand2 size={16} />
              Optimize
            </Button>
            <Button disabled={!simulation} onClick={exportSimulation} type="button" variant="ghost">
              <Download size={16} />
              Export
            </Button>
          </div>
        </div>
      </header>

      {error && (
        <div className="shrink-0 border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mx-auto grid min-h-0 w-full max-w-[1640px] flex-1 grid-cols-1 gap-3 p-3 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <aside className="flex min-h-0 flex-col">
          <SidePanelTabs
            importPanel={
              <ImportPanel loading={loading} onImport={handleImport} onLoadSample={handleLoadSample} />
            }
            cycleSelector={
              availableCycles.length > 1 ? (
                <CycleSelector
                  cycles={availableCycles}
                  activeCycleId={activeCycleId}
                  onSelect={selectCycle}
                  excludedIds={groupSummary?.exclusion.excluded.map((entry) => entry.cycle_id)}
                />
              ) : undefined
            }
            groupOverview={
              groupSummary ? <GroupOverview summary={groupSummary} cycles={availableCycles} /> : undefined
            }
            diagnosis={
              data?.analysis.diagnosis ? <DiagnosisPanel diagnosis={data.analysis.diagnosis} /> : undefined
            }
            notes={simulation ? <SimulationNotes simulation={simulation} /> : undefined}
            excludedCount={groupSummary?.exclusion.excluded_count}
          />
        </aside>

        <section className="flex min-h-0 flex-col gap-3">
          {data && (
            <Card className="flex min-h-0 flex-1 flex-col overflow-hidden border-slate-300">
              <CardHeader className="flex shrink-0 flex-col gap-2 md:flex-row md:items-start md:justify-between">
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
              <CardContent className="min-h-0 flex-1 p-2">
                <WaveformChart
                  predicted={predictedWaveform}
                  segments={data.analysis.segments}
                  waveform={data.cycle.waveform}
                />
              </CardContent>
            </Card>
          )}

          {currentFeatures && (
            <Card className="shrink-0 border-slate-300">
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

        <aside
          aria-label="Right control rail"
          className="flex min-h-0 flex-col gap-3 overflow-y-auto"
        >
          {currentSettings && candidateSettings && (
            <SettingsPanel
              candidate={candidateSettings}
              current={currentSettings}
              loading={loading || liveSimulating}
              onChange={updateCandidateSettings}
              onSimulate={handleSimulate}
            />
          )}

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
    </main>
  );
}

export default App;

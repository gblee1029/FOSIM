import { CheckCircle2 } from "lucide-react";

import { candidateLabel, confidenceTone, formatNumber, settingDelta } from "../lib/format";
import type { CandidateEvaluation, FasteningSettings } from "../types/domain";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

type Props = {
  candidates: CandidateEvaluation[];
  current: FasteningSettings;
  layout?: "grid" | "rail";
  selectedLabel?: string;
  onSelect: (candidate: CandidateEvaluation) => void;
};

export function CandidateCards({ candidates, current, layout = "grid", selectedLabel, onSelect }: Props) {
  const shellClass =
    layout === "rail" ? "space-y-3" : "grid grid-cols-1 gap-3 xl:grid-cols-3";
  return (
    <div className={shellClass}>
      {candidates.map((candidate) => {
        const features = candidate.simulation.predicted_features;
        return (
          <Card
            key={candidate.label}
            className={selectedLabel === candidate.label ? "border-graphite" : ""}
          >
            <CardHeader className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle>{candidateLabel(candidate.label)}</CardTitle>
                <Badge className={confidenceTone(candidate.simulation.confidence.level)}>
                  {candidate.simulation.confidence.level}
                </Badge>
              </div>
              <div className="flex items-end justify-between">
                <div className="font-mono text-2xl font-semibold text-graphite">
                  {candidate.score.toFixed(1)}
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  score
                </span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 rounded-md bg-slate-50 p-2 font-mono">
                <span>Speed {settingDelta(current.target_speed, candidate.settings.target_speed, "RPM")}</span>
                <span>
                  Rising{" "}
                  {settingDelta(
                    current.clamp_rising_time,
                    candidate.settings.clamp_rising_time,
                    "ms",
                  )}
                </span>
                <span>
                  Hold{" "}
                  {settingDelta(current.torque_hold_time, candidate.settings.torque_hold_time, "ms")}
                </span>
                <span>
                  Torque{" "}
                  {settingDelta(current.target_torque, candidate.settings.target_torque, "Nm")}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 border-y border-slate-100 py-3">
                <Metric label="Final" value={formatNumber(features.final_torque, "Nm", 3)} />
                <Metric label="Over" value={formatNumber(features.overshoot_percent, "%", 2)} />
                <Metric label="Time" value={formatNumber(features.total_time, "ms", 0)} />
              </div>
              <p className={layout === "rail" ? "text-steel" : "min-h-10 text-steel"}>
                {candidate.reason}
              </p>
              <Button className="w-full" onClick={() => onSelect(candidate)} type="button" variant="secondary">
                <CheckCircle2 size={15} />
                Compare
              </Button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="font-mono text-graphite">{value}</div>
    </div>
  );
}

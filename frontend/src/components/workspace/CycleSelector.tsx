import type { AnalyzedCycle } from "../../types/domain";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

type Props = {
  cycles: AnalyzedCycle[];
  activeCycleId?: string;
  onSelect: (cycleId: string) => void;
};

export function CycleSelector({ cycles, activeCycleId, onSelect }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Input waveforms</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <select
          className="w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-graphite"
          value={activeCycleId ?? cycles[0]?.cycle.cycle_id ?? ""}
          onChange={(event) => onSelect(event.target.value)}
        >
          {cycles.map((entry) => (
            <option key={entry.cycle.cycle_id} value={entry.cycle.cycle_id}>
              {entry.cycle.cycle_id}
            </option>
          ))}
        </select>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Loaded</div>
            <div className="font-mono text-graphite">{cycles.length}</div>
          </div>
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Active</div>
            <div className="truncate font-mono text-graphite">{activeCycleId ?? "-"}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

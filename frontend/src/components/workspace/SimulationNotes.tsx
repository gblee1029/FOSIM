import type { SimulationResult } from "../../types/domain";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

export function SimulationNotes({ simulation }: { simulation: SimulationResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Simulation notes</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <NoteList title="Confidence factors" items={simulation.confidence.factors} />
        <NoteList title="Warnings" items={simulation.warnings.length ? simulation.warnings : ["No MVP warning."]} />
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

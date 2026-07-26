import type { Diagnosis } from "../types/domain";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

type Props = {
  diagnosis: Diagnosis;
};

export function DiagnosisPanel({ diagnosis }: Props) {
  const tone =
    diagnosis.severity === "normal"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : diagnosis.severity === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : "border-slate-200 bg-slate-50 text-steel";
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Diagnosis</CardTitle>
        <Badge className={tone}>{diagnosis.anomaly_type}</Badge>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-steel">{diagnosis.description}</p>
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Evidence
          </div>
          <ul className="space-y-1 font-mono text-xs text-graphite">
            {diagnosis.evidence_features.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        {diagnosis.related_parameters.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {diagnosis.related_parameters.map((item) => (
              <Badge key={item} className="border-slate-200 bg-white text-steel">
                {item}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

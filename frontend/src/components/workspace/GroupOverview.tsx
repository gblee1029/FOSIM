import type { AnalyzedCycle, GroupSummary } from "../../types/domain";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

type Props = {
  summary: GroupSummary;
  cycles: AnalyzedCycle[];
};

const GRADE_LABEL: Record<string, string> = {
  reference: "참고 수준 (표본 5개 미만)",
  moderate: "보통 (표본 5~19개)",
  statistical: "통계적 유의 (표본 20개 이상)",
};

export function GroupOverview({ summary, cycles }: Props) {
  const finalTorque = summary.distributions.final_torque;
  const cpk = summary.capability.final_torque_cpk;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cycle group</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {!summary.is_single_group && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-2 text-amber-800">
            설정이 다른 그룹이 {summary.groups.length}개 있습니다. 최적화는 첫 번째 그룹만 사용합니다.
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Cycles</div>
            <div className="font-mono text-graphite">{cycles.length}</div>
          </div>
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Optimization basis</div>
            <div className="font-mono text-graphite">{summary.exclusion.included_count}</div>
          </div>
          {finalTorque && (
            <>
              <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
                <div className="text-slate-400">Final torque mean</div>
                <div className="font-mono text-graphite">{finalTorque.mean.toFixed(3)}</div>
              </div>
              <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
                <div className="text-slate-400">Final torque std</div>
                <div className="font-mono text-graphite">{finalTorque.std.toFixed(4)}</div>
              </div>
            </>
          )}
          {cpk !== undefined && (
            <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
              <div className="text-slate-400">Cpk</div>
              <div className="font-mono text-graphite">{cpk.toFixed(2)}</div>
            </div>
          )}
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="text-slate-400">Confidence</div>
            <div className="text-graphite">
              {GRADE_LABEL[summary.confidence_grade] ?? summary.confidence_grade}
            </div>
          </div>
        </div>
        {summary.exclusion.excluded.length > 0 && (
          <div className="rounded-md border border-slate-100 bg-white px-2 py-2">
            <div className="mb-1 text-slate-400">
              최적화 기준에서 제외 {summary.exclusion.excluded_count}건
            </div>
            <ul className="space-y-1">
              {summary.exclusion.excluded.map((entry) => (
                <li key={entry.cycle_id} className="font-mono text-graphite">
                  {entry.cycle_id} — {entry.reason}: {entry.detail}
                </li>
              ))}
            </ul>
          </div>
        )}
        {summary.exclusion.warnings.map((warning) => (
          <div
            key={warning}
            className="rounded-md border border-amber-200 bg-amber-50 px-2 py-2 text-amber-800"
          >
            {warning}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

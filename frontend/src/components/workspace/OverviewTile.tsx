import type { OverviewStat } from "../../lib/overviewStats";

export function OverviewTile({ label, value, delta, icon: Icon, accent }: OverviewStat) {
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

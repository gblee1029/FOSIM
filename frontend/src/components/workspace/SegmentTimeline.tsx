import type { Segments } from "../../types/domain";

type TimelineKey = "engage_start_time" | "seating_time" | "target_reach_time" | "hold_end_time" | "stop_time";

const timelineItems: Array<{ key: TimelineKey; label: string }> = [
  { key: "engage_start_time", label: "Engage" },
  { key: "seating_time", label: "Seat" },
  { key: "target_reach_time", label: "Target" },
  { key: "hold_end_time", label: "Hold" },
  { key: "stop_time", label: "Stop" },
];

export function SegmentTimeline({ segments }: { segments: Segments }) {
  const start = segments.start_time;
  const span = Math.max(segments.stop_time - start, 1);

  return (
    <div className="w-full max-w-md rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="relative h-8">
        <div className="absolute left-0 right-0 top-4 h-px bg-slate-300" />
        {timelineItems.map(({ key, label }) => {
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

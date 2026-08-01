import { useEffect, useMemo, useRef } from "react";
import * as echarts from "echarts";

import type { Segments, WaveformSample } from "../types/domain";

type Props = {
  waveform: WaveformSample[];
  predicted?: WaveformSample[];
  segments?: Segments;
};

const markerNames: Array<[keyof Segments, string]> = [
  ["engage_start_time", "Engage"],
  ["seating_time", "Seating"],
  ["target_reach_time", "Target"],
  ["hold_end_time", "Hold end"],
  ["stop_time", "Stop"],
];

export function WaveformChart({ waveform, predicted, segments }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const option = useMemo(() => {
    const markLine = segments
      ? {
          symbol: "none",
          label: { formatter: "{b}", color: "#1d2326", fontSize: 11 },
          lineStyle: { color: "#7c8790", type: "dashed", width: 1 },
          data: markerNames.map(([key, name]) => ({ name, xAxis: segments[key] as number })),
        }
      : undefined;
    return {
      animation: false,
      color: ["#c44d36", "#7a1f14", "#287a73", "#425cc7"],
      tooltip: { trigger: "axis" },
      legend: {
        top: 0,
        textStyle: { color: "#526168" },
      },
      grid: { left: 52, right: 54, top: 42, bottom: 42 },
      xAxis: {
        type: "value",
        name: "ms",
        nameLocation: "middle",
        nameGap: 28,
        axisLine: { lineStyle: { color: "#87919a" } },
        splitLine: { lineStyle: { color: "#edf0f2" } },
      },
      yAxis: [
        {
          type: "value",
          name: "Torque Nm",
          axisLine: { lineStyle: { color: "#c44d36" } },
          splitLine: { lineStyle: { color: "#edf0f2" } },
        },
        {
          type: "value",
          name: "RPM / deg",
          axisLine: { lineStyle: { color: "#287a73" } },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: "inside", filterMode: "none" },
        { type: "slider", height: 18, bottom: 8, filterMode: "none" },
      ],
      series: [
        {
          name: "Current torque",
          type: "line",
          yAxisIndex: 0,
          showSymbol: false,
          lineStyle: { width: 2 },
          data: waveform.map((sample) => [sample.time_ms, sample.torque]),
          markLine,
        },
        predicted
          ? {
              name: "Predicted torque",
              type: "line",
              yAxisIndex: 0,
              showSymbol: false,
              lineStyle: { width: 2, type: "dashed" },
              data: predicted.map((sample) => [sample.time_ms, sample.torque]),
            }
          : undefined,
        {
          name: "Speed",
          type: "line",
          yAxisIndex: 1,
          showSymbol: false,
          lineStyle: { width: 1.5 },
          data: waveform.map((sample) => [sample.time_ms, sample.speed ?? 0]),
        },
        {
          name: "Angle",
          type: "line",
          yAxisIndex: 1,
          showSymbol: false,
          lineStyle: { width: 1.5 },
          data: waveform.map((sample) => [sample.time_ms, sample.angle ?? 0]),
        },
      ].filter(Boolean),
    };
  }, [predicted, segments, waveform]);

  // 차트 인스턴스는 마운트 시 1회만 만든다. 매번 재생성하면 사용자의 확대(dataZoom)
  // 상태가 초기화된다.
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const chart = echarts.init(element);
    chartRef.current = chart;

    // 창 크기가 그대로여도 컨테이너 높이는 바뀐다(탭 전환, 특징 표 등장 등).
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    // 예측 파형이 생기거나 사라지면 series 개수가 바뀌므로 series만 교체한다.
    // 통째로 notMerge하면 dataZoom 위치까지 초기화된다.
    chartRef.current?.setOption(option, { replaceMerge: ["series"] });
  }, [option]);

  return <div ref={ref} className="h-full min-h-[320px] w-full" />;
}

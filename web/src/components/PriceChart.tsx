"use client";
import { useEffect, useRef } from "react";
import { CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, LineStyle } from "lightweight-charts";

type Bar = { time: string; open: number; high: number; low: number; close: number; volume: number };

function addDays(d: string, n: number) {
  const x = new Date(d + "T00:00:00Z"); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10);
}

export default function PriceChart({ bars, forecast, dark }: { bars: Bar[]; forecast?: any; dark: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !bars.length) return;
    const chart = createChart(ref.current, {
      height: 360, autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: dark ? "#cbd5e1" : "#334155" },
      grid: { vertLines: { color: dark ? "#1e293b" : "#eef2f7" }, horzLines: { color: dark ? "#1e293b" : "#eef2f7" } },
      rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false },
    });
    const c = chart.addSeries(CandlestickSeries, { upColor: "#10b981", downColor: "#ef4444", wickUpColor: "#10b981", wickDownColor: "#ef4444", borderVisible: false });
    c.setData(bars.map((b) => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })));
    const v = chart.addSeries(HistogramSeries, { priceScaleId: "vol", color: dark ? "#334155" : "#cbd5e1", priceFormat: { type: "volume" } });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    v.setData(bars.map((b) => ({ time: b.time, value: b.volume })));
    if (forecast) {
      const last = bars[bars.length - 1];
      const end = addDays(last.time, 7);
      const mk = (r: number, color: string, style: LineStyle) => {
        const s = chart.addSeries(LineSeries, { color, lineWidth: 2, lineStyle: style, priceLineVisible: false, lastValueVisible: true });
        s.setData([{ time: last.time, value: last.close }, { time: end, value: last.close * Math.exp(r) }]);
      };
      mk(forecast.p90_5d, "#94a3b8", LineStyle.Dashed);
      mk(forecast.exp_ret_5d, "#c8962e", LineStyle.Solid);
      mk(forecast.p10_5d, "#94a3b8", LineStyle.Dashed);
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [bars, forecast, dark]);
  return <div ref={ref} className="w-full" />;
}

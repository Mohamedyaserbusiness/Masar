"use client";
import { useEffect, useRef, useState } from "react";
import { api, num, pct, WS } from "@/lib/api";
import { useApp } from "@/lib/i18n";
import { Card, Change, SourceBadge } from "@/components/ui";
import PriceChart from "@/components/PriceChart";

export default function Markets() {
  const { t, lang, dark } = useApp();
  const [rows, setRows] = useState<any[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [fc, setFc] = useState<Record<string, any>>({});
  const [tab, setTab] = useState<"EGX" | "US">("EGX");
  const [sel, setSel] = useState("COMI");
  const [hist, setHist] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const prev = useRef<Record<string, number>>({});
  const [flash, setFlash] = useState<Record<string, string>>({});

  useEffect(() => {
    api("/market/universe").then((u) => { setRows(u.symbols); setStatus(u.status); setFc(u.forecasts); });
    api("/market/model-report").then(setReport);
    let ws: WebSocket; let stop = false;
    const connect = () => {
      ws = new WebSocket(WS + "/ws/market");
      ws.onmessage = (m) => {
        const d = JSON.parse(m.data);
        const f: Record<string, string> = {};
        for (const r of d.data) { const p = prev.current[r.symbol]; if (p != null && p !== r.price) f[r.symbol] = r.price > p ? "flash-up" : "flash-down"; prev.current[r.symbol] = r.price; }
        setFlash(f); setRows(d.data); setStatus(d.status);
      };
      ws.onclose = () => { if (!stop) setTimeout(connect, 2000); };
    };
    connect();
    return () => { stop = true; ws?.close(); };
  }, []);
  useEffect(() => { api(`/market/candles/${encodeURIComponent(sel)}?days=180`).then(setHist).catch(() => setHist(null)); }, [sel]);

  const fx = rows.filter((r) => r.market === "FX");
  const list = rows.filter((r) => r.market === tab);
  const cur = rows.find((r) => r.symbol === sel);
  const f = fc[sel];
  const m = report?.forecast?.mean;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        {status && (["EGX", "US"] as const).map((k) => (
          <div key={k} className="card !p-4">
            <div className="flex items-center justify-between"><b>{k === "EGX" ? (lang === "ar" ? "البورصة المصرية" : "Egyptian Exchange") : (lang === "ar" ? "السوق الأمريكي" : "US market")}</b>
              <span className={`chip ${status[k].open ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}>{status[k].open ? t("open") : t("closed")}</span></div>
            <div className="mt-1 text-xs muted">{status[k].hours} · Cairo {status.cairo_time}</div>
          </div>
        ))}
        {fx.map((r) => (
          <div key={r.symbol} className={`card !p-4 ${flash[r.symbol] || ""}`}>
            <div className="text-xs muted">{lang === "ar" ? r.name_ar : r.name}</div>
            <div className="flex items-end justify-between"><b className="text-xl num">{num(r.price, lang, r.symbol === "USD/EGP" ? 3 : 1)}</b><Change v={r.change_pct} /></div>
          </div>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-2" title={t("markets")} right={
          <div className="flex gap-1">{(["EGX", "US"] as const).map((k) => <button key={k} onClick={() => { setTab(k); setSel(k === "EGX" ? "COMI" : "AAPL"); }} className={`chip ${tab === k ? "bg-brand-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>{k}</button>)}</div>}>
          <div className="max-h-[520px] overflow-y-auto">
            <table className="w-full text-sm">
              <tbody>{list.map((r) => (
                <tr key={r.symbol} onClick={() => setSel(r.symbol)} className={`cursor-pointer border-t border-slate-100 dark:border-slate-800 ${flash[r.symbol] || ""} ${sel === r.symbol ? "bg-brand-50 dark:bg-brand-700/20" : ""}`}>
                  <td className="py-2"><b>{r.symbol}</b> {r.sharia && <span title="Sharia-compliant" className="text-xs">☪</span>}<div className="text-xs muted">{lang === "ar" ? r.name_ar : r.name}</div></td>
                  <td className="text-end num font-semibold">{num(r.price, lang)}</td>
                  <td className="text-end"><Change v={r.change_pct} /></td>
                  <td className="text-end">{fc[r.symbol] && <span className={`chip ${fc[r.symbol].prob_up >= 0.5 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>{Math.round(fc[r.symbol].prob_up * 100)}%↑</span>}</td>
                </tr>))}</tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs muted"><SourceBadge source={list[0]?.source} /> {tab === "EGX" ? (lang === "ar" ? "لا يوجد مصدر مجاني مرخّص لبيانات البورصة المصرية — أسعار محاكاة" : "No licensed free EGX feed — simulated prices (EODHD/ICE in production)") : "Finnhub WebSocket when a key is set"}</div>
        </Card>

        <div className="space-y-5 lg:col-span-3">
          <Card title={<span>{sel} · {cur && (lang === "ar" ? cur.name_ar : cur.name)} {cur && <span className="ms-2 num">{num(cur.price, lang)}</span>}</span>} right={<SourceBadge source={hist?.daily?.[0]?.source} />}>
            {hist ? <PriceChart bars={hist.daily} forecast={f} dark={dark} /> : <div className="h-[360px]" />}
            <div className="mt-2 text-xs muted">— {lang === "ar" ? "الخط الذهبي: التوقع الأوسط لخمسة أيام، والمتقطع: نطاق 80%" : "Gold line: median 5-day forecast · dashed: 80% range"}</div>
          </Card>
          {f && (
            <div className="grid gap-4 md:grid-cols-2">
              <Card title={t("forecast")}>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div><dt className="muted">{t("probUp")}</dt><dd className="text-xl font-bold num">{pct(f.prob_up, lang, 0)}</dd></div>
                  <div><dt className="muted">{t("expRet")}</dt><dd className={`text-xl font-bold num ${f.exp_ret_5d >= 0 ? "text-emerald-600" : "text-red-600"}`}>{pct(Math.exp(f.exp_ret_5d) - 1, lang, 2)}</dd></div>
                  <div><dt className="muted">{t("range")}</dt><dd className="num">{pct(Math.exp(f.p10_5d) - 1, lang)} … {pct(Math.exp(f.p90_5d) - 1, lang)}</dd></div>
                  <div><dt className="muted">{t("confidence")}</dt><dd><span className="chip bg-slate-100 dark:bg-slate-800">{f.confidence}</span> · vol {pct(f.vol_annual, lang, 0)}</dd></div>
                </dl>
              </Card>
              {m && (
                <Card title={t("modelHonesty")}>
                  <div className="text-xs muted">{report.forecast.validation}</div>
                  <table className="mt-2 w-full text-sm"><tbody>
                    <tr><td>LightGBM accuracy</td><td className="text-end num font-bold">{pct(m.model_acc, lang)}</td></tr>
                    <tr><td>Baseline “always up”</td><td className="text-end num">{pct(m.always_up_acc, lang)}</td></tr>
                    <tr><td>Baseline momentum</td><td className="text-end num">{pct(m.momentum_acc, lang)}</td></tr>
                    <tr><td>Shuffled-label (leak test)</td><td className="text-end num">{pct(report.forecast.shuffled_label_acc, lang)}</td></tr>
                  </tbody></table>
                  <div className="mt-2 text-xs muted">{report.forecast.note}</div>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

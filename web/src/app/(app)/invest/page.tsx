"use client";
import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { api, num, pct } from "@/lib/api";
import { useApp } from "@/lib/i18n";
import { Card, COLORS } from "@/components/ui";

const Q = [
  { k: "horizon", en: "When will you need this money?", ar: "إمتى هتحتاج الفلوس دي؟", o: [["< 1 year", "أقل من سنة"], ["1–2 years", "1–2 سنة"], ["3–5 years", "3–5 سنين"], ["5–10 years", "5–10 سنين"], ["10+ years", "أكتر من 10"]] },
  { k: "experience", en: "Your investing experience?", ar: "خبرتك في الاستثمار؟", o: [["None", "مفيش"], ["Bank CDs only", "شهادات بنكية بس"], ["Funds / gold", "صناديق / ذهب"], ["Stocks", "أسهم"], ["Active trader", "متداول نشط"]] },
  { k: "drawdown", en: "If your portfolio fell 20% you would…", ar: "لو محفظتك نزلت 20% هتعمل إيه؟", o: [["Sell everything", "أبيع كل حاجة"], ["Sell some", "أبيع جزء"], ["Wait", "أستنى"], ["Buy a little more", "أشتري شوية"], ["Buy a lot more", "أشتري كتير"]] },
  { k: "goal", en: "Main goal?", ar: "هدفك الأساسي؟", o: [["Protect capital", "حماية رأس المال"], ["Regular income", "دخل ثابت"], ["Balanced", "متوازن"], ["Growth", "نمو"], ["Maximum growth", "أقصى نمو"]] },
  { k: "share", en: "Share of savings to invest?", ar: "نسبة مدخراتك اللي هتستثمرها؟", o: [["< 10%", "أقل من 10%"], ["10–25%", "10–25%"], ["25–50%", "25–50%"], ["50–75%", "50–75%"], ["> 75%", "أكتر من 75%"]] },
];

export default function Invest() {
  const { t, lang } = useApp();
  const [ans, setAns] = useState<Record<string, number>>({ horizon: 3, experience: 3, drawdown: 3, goal: 3, share: 3 });
  const [r, setR] = useState<any>(null);
  const [sharia, setSharia] = useState<boolean | null>(null);
  const [editing, setEditing] = useState(false);
  const load = (s: boolean | null) => api(`/invest/recommendations${s === null ? "" : `?sharia=${s}`}`).then((x) => { setR(x); if (x.needs_profile) setEditing(true); if (s === null && !x.needs_profile) setSharia(x.sharia_only); });
  useEffect(() => { load(null); }, []);
  async function save() { await api("/invest/risk-profile", { body: ans }); setEditing(false); load(sharia); }
  return (
    <div className="space-y-5">
      {(editing || r?.needs_profile) ? (
        <Card title={t("riskQuiz")}>
          <div className="grid gap-4 md:grid-cols-2">
            {Q.map((q) => (
              <div key={q.k}><div className="label !text-sm">{lang === "ar" ? q.ar : q.en}</div>
                <div className="flex flex-wrap gap-2">{q.o.map((o, i) => (
                  <button key={i} onClick={() => setAns({ ...ans, [q.k]: i + 1 })} className={`chip !py-1.5 ${ans[q.k] === i + 1 ? "bg-brand-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>{lang === "ar" ? o[1] : o[0]}</button>))}</div>
              </div>))}
          </div>
          <button className="btn-primary mt-5" onClick={save}>{lang === "ar" ? "احسب ملفي" : "Calculate my profile"}</button>
        </Card>
      ) : r && (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card title={t("riskQuiz")} right={<button className="btn-ghost !py-1 text-xs" onClick={() => setEditing(true)}>{lang === "ar" ? "تعديل" : "Edit"}</button>}>
              <div className="text-3xl font-bold text-brand-600">{lang === "ar" ? r.label[1] : r.label[0]}</div>
              <div className="mt-1 flex gap-1">{[1, 2, 3, 4, 5].map((i) => <div key={i} className={`h-2 flex-1 rounded ${i <= r.band ? "bg-brand-500" : "bg-slate-200 dark:bg-slate-800"}`} />)}</div>
              <ul className="mt-3 text-sm muted">{r.notes.map((n: string) => <li key={n}>• {n}</li>)}</ul>
              <label className="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" checked={!!sharia} onChange={(e) => { setSharia(e.target.checked); load(e.target.checked); }} />☪ {t("shariaOnly")}</label>
            </Card>
            <Card title={t("allocation")} className="lg:col-span-2">
              <div className="h-60"><ResponsiveContainer><PieChart>
                <Pie data={Object.entries(r.allocation).filter(([, v]) => (v as number) > 0).map(([name, value]) => ({ name, value }))} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} label={(e: any) => `${e.value}%`}>
                  {Object.keys(r.allocation).map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie><Tooltip /><Legend layout="vertical" align="right" verticalAlign="middle" /></PieChart></ResponsiveContainer></div>
            </Card>
          </div>
          <Card title={t("recommendations")} right={<span className="text-xs muted">{t("disclaimer")}</span>}>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {r.picks.map((p: any) => (
                <div key={p.symbol} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                  <div className="flex items-start justify-between">
                    <div><b className="text-lg">{p.symbol}</b> <span className="chip bg-slate-100 dark:bg-slate-800">{p.market}</span> {p.sharia && <span className="chip bg-emerald-50 text-emerald-700">☪</span>}
                      <div className="text-sm muted">{lang === "ar" ? p.name_ar : p.name} · {p.sector}</div></div>
                    <div className="text-end"><div className="font-bold num">{num(p.last_close, lang)}</div><div className="text-xs muted">{p.market === "US" ? "USD" : "EGP"}</div></div>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800"><div className="muted">P(up)</div><b className="num">{pct(p.prob_up, lang, 0)}</b></div>
                    <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800"><div className="muted">5d</div><b className="num">{pct(Math.exp(p.exp_ret_5d) - 1, lang, 1)}</b></div>
                    <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800"><div className="muted">Vol</div><b className="num">{pct(p.vol_annual, lang, 0)}</b></div>
                  </div>
                  <div className="mt-3 text-xs font-semibold muted">{t("why")}</div>
                  <ul className="text-sm">{p.why.map((w: string) => <li key={w}>✓ {w}</li>)}</ul>
                </div>))}
            </div>
            <p className="mt-4 text-xs muted">{r.disclaimer}</p>
          </Card>
        </>
      )}
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Area, AreaChart } from "recharts";
import { AlertTriangle } from "lucide-react";
import { api, egp, pct, WS } from "@/lib/api";
import { useApp } from "@/lib/i18n";
import { Card, COLORS, Gauge, Stat } from "@/components/ui";

export default function Dashboard() {
  const { t, lang } = useApp();
  const [o, setO] = useState<any>(null);
  const [a, setA] = useState<any>(null);
  const [tx, setTx] = useState<any[]>([]);
  const [alert, setAlert] = useState<any>(null);
  const load = () => api("/me/transactions?limit=15").then(setTx);
  useEffect(() => {
    api("/me/overview").then(setO); api("/me/analytics").then(setA); load();
    const ws = new WebSocket(WS + "/ws/events");
    ws.onmessage = (m) => { const e = JSON.parse(m.data); if (e.type === "transaction") { load(); if (e.flagged) setAlert(e); } };
    return () => ws.close();
  }, []);
  if (!o || !a) return <div className="muted">Loading…</div>;
  const k = o.kpis, c = o.customer;
  const respond = async (action: string) => { await api(`/me/alerts/${alert.alert_id}`, { body: { action } }); setAlert(null); };
  return (
    <div className="space-y-5">
      {alert && (
        <div className="card flex flex-wrap items-center gap-4 border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/40">
          <AlertTriangle className="text-red-600" />
          <div className="flex-1">
            <div className="font-bold">{t("wasThisYou")} — {egp(alert.tx.amount, lang)} · {alert.tx.merchant} · {alert.tx.governorate}</div>
            <div className="text-sm muted">Risk {alert.risk_score}/100 · {alert.reasons.join(" · ")}</div>
          </div>
          <button className="btn-ghost" onClick={() => respond("confirm")}>{t("itWasMe")}</button>
          <button className="btn-primary !bg-red-600" onClick={() => respond("fraud")}>{t("notMe")}</button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label={t("totalBalance")} value={egp(k.total_balance_egp, lang)} sub={`${o.accounts.length} ${t("accounts")}`} />
        <Stat label={t("income")} value={egp(k.monthly_income, lang)} sub={lang === "ar" ? c.occupation_ar : c.occupation_en} />
        <Stat label={t("spend")} value={egp(k.monthly_spend, lang)} />
        <Stat label={t("savingsRate")} value={pct(k.savings_rate, lang)} tone={k.savings_rate >= 0.1 ? "up" : "down"} sensitive={false} />
        <Stat label={t("netWorth")} value={egp(k.net_worth, lang)} sub={`${t("cds")} ${egp(k.certificates, lang)}`} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={t("health")}>
          <Gauge value={k.health_score} />
          <ul className="mt-3 space-y-1 text-sm">
            <li>• {lang === "ar" ? "صندوق الطوارئ" : "Emergency fund"}: <b>{k.emergency_months} {lang === "ar" ? "شهور" : "months"}</b></li>
            <li>• {lang === "ar" ? "نسبة الأقساط للدخل" : "Debt-to-income"}: <b>{pct(k.dti, lang)}</b></li>
            <li>• I-Score: <b>{c.credit_score}</b> · {c.segment} · {lang === "ar" ? c.governorate_ar : c.governorate_en}</li>
          </ul>
        </Card>
        <Card title={t("spendByCat")} className="lg:col-span-2">
          <div className="h-64"><ResponsiveContainer>
            <PieChart>
              <Pie data={a.by_category_90d} dataKey="amount" nameKey={lang === "ar" ? "label_ar" : "label"} innerRadius={55} outerRadius={95} paddingAngle={2}>
                {a.by_category_90d.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: any) => egp(v, lang)} /><Legend layout="vertical" align="right" verticalAlign="middle" />
            </PieChart>
          </ResponsiveContainer></div>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("incomeVsSpend")}>
          <div className="h-64"><ResponsiveContainer>
            <BarChart data={a.monthly}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="month" fontSize={11} /><YAxis fontSize={11} width={60} />
              <Tooltip formatter={(v: any) => egp(v, lang)} /><Legend /><Bar dataKey="income" fill="#0f8a6a" radius={[4, 4, 0, 0]} /><Bar dataKey="spend" fill="#c8962e" radius={[4, 4, 0, 0]} /></BarChart>
          </ResponsiveContainer></div>
        </Card>
        <Card title={t("dailySpend")}>
          <div className="h-64"><ResponsiveContainer>
            <AreaChart data={a.daily_60d}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="day" fontSize={11} /><YAxis fontSize={11} width={60} />
              <Tooltip formatter={(v: any) => egp(v, lang)} /><Area dataKey="amount" stroke="#0f8a6a" fill="#0f8a6a33" /></AreaChart>
          </ResponsiveContainer></div>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={t("peers")}>
          <div className="h-56"><ResponsiveContainer>
            <BarChart data={a.peer_benchmark} layout="vertical"><XAxis type="number" fontSize={10} /><YAxis type="category" dataKey="label" width={110} fontSize={10} />
              <Tooltip formatter={(v: any) => egp(v, lang)} /><Legend /><Bar dataKey="you" name={t("you")} fill="#0f8a6a" /><Bar dataKey="peers" name={t("peersL")} fill="#94a3b8" /></BarChart>
          </ResponsiveContainer></div>
        </Card>
        <Card title={t("subscriptions")}>
          <ul className="space-y-2 text-sm">{a.subscriptions.slice(0, 7).map((s: any) => (
            <li key={s.merchant} className="flex justify-between"><span>{s.merchant} <span className="muted">· {s.n_months} mo</span></span><b className="num sensitive">{egp(s.avg_amount, lang)}</b></li>))}
            {!a.subscriptions.length && <li className="muted">—</li>}
          </ul>
        </Card>
        <Card title={t("accounts")}>
          <ul className="space-y-2 text-sm">
            {o.accounts.map((x: any) => <li key={x.account_id} className="flex justify-between"><span>{x.type} <span className="muted num">{x.iban}</span></span><b className="num sensitive">{x.currency === "USD" ? `$${x.balance.toLocaleString()}` : egp(x.balance, lang)}</b></li>)}
            {o.cards.map((x: any, i: number) => <li key={i} className="flex justify-between"><span>💳 {x.card_type} •••• {x.last4}</span><span className="muted">{x.credit_limit ? egp(x.credit_limit, lang) : x.expiry}</span></li>)}
            {o.loans.map((x: any, i: number) => <li key={"l" + i} className="flex justify-between"><span>🏦 {x.loan_type} · {x.rate}%</span><b className="num sensitive">{egp(x.monthly_installment, lang)}/mo</b></li>)}
            {o.certificates.map((x: any, i: number) => <li key={"c" + i} className="flex justify-between"><span>📜 CD {x.term_years}y · {x.rate}%</span><b className="num sensitive">{egp(x.amount, lang)}</b></li>)}
          </ul>
        </Card>
      </div>
      <Card title={t("recent")}>
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <tbody>{tx.map((r, i) => (
            <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
              <td className="py-2 muted num">{String(r.ts).slice(0, 16).replace("T", " ")}</td>
              <td>{r.merchant} {r.live && <span className={`chip ms-1 ${r.flagged ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"}`}>{r.flagged ? `⚠ risk ${r.risk_score}` : "live"}</span>}</td>
              <td className="muted">{r.category} · {r.channel}</td><td className="muted">{r.governorate}</td>
              <td className={`text-end font-semibold num sensitive ${r.direction === "credit" ? "text-emerald-600" : ""}`}>{r.direction === "credit" ? "+" : "−"}{egp(r.amount, lang, 2)}</td>
            </tr>))}</tbody>
        </table></div>
      </Card>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { api, egp, num, pct, WS } from "@/lib/api";
import { useApp } from "@/lib/i18n";
import { useMe } from "@/components/Shell";
import { Card, COLORS, Stat } from "@/components/ui";

type Tab = "overview" | "fraud" | "customer360" | "governance" | "models";

export default function Staff() {
  const { t, lang } = useApp();
  const me = useMe();
  const [tab, setTab] = useState<Tab>("overview");
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">{(["overview", "fraud", "customer360", "governance", "models"] as Tab[]).map((k) => (
        <button key={k} onClick={() => setTab(k)} className={`btn ${tab === k ? "bg-brand-600 text-white" : "btn-ghost"}`}>{t(k)}</button>))}</div>
      {tab === "overview" && <Overview lang={lang} />}
      {tab === "fraud" && <Fraud lang={lang} canTriage={me?.role !== "advisor"} />}
      {tab === "customer360" && <C360 lang={lang} canReveal={me?.role === "compliance"} />}
      {tab === "governance" && <Gov />}
      {tab === "models" && <Models lang={lang} />}
    </div>
  );
}

function Overview({ lang }: { lang: string }) {
  const [d, setD] = useState<any>(null);
  useEffect(() => { api("/staff/overview").then(setD); }, []);
  if (!d) return <div className="muted">Loading…</div>;
  const k = d.kpis;
  const monthly: any[] = Object.values(d.monthly.reduce((acc: any, r: any) => { (acc[r.month] ||= { month: r.month })[r.direction] = r.amount / 1e6; return acc; }, {}));
  return (<>
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Stat sensitive={false} label="Customers" value={num(k.customers, lang, 0)} sub={`${num(k.investors, lang, 0)} investors`} />
      <Stat sensitive={false} label="EGP deposits" value={egp(k.deposits_egp / 1e9, lang, 2) + " bn"} sub={`CDs ${egp(k.cds_egp / 1e9, lang, 2)} bn`} />
      <Stat sensitive={false} label="Loan book" value={egp(k.loans_egp / 1e9, lang, 2) + " bn"} sub={`NPL (90+ DPD) ${pct(k.npl_ratio, lang)}`} />
      <Stat sensitive={false} label="Transactions (12m)" value={num(k.transactions / 1e6, lang, 2) + " M"} sub={`${d.open_alerts} open alerts`} />
    </div>
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="Customers by governorate" className="lg:col-span-2"><div className="h-80"><ResponsiveContainer>
        <BarChart data={d.by_governorate}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey={lang === "ar" ? "gov_ar" : "gov"} fontSize={10} angle={-40} textAnchor="end" height={70} interval={0} /><YAxis fontSize={11} /><Tooltip /><Bar dataKey="customers" fill="#0f8a6a" radius={[4, 4, 0, 0]} /></BarChart>
      </ResponsiveContainer></div></Card>
      <Card title="Segments"><div className="h-80"><ResponsiveContainer><PieChart>
        <Pie data={d.by_segment} dataKey="n" nameKey="segment" innerRadius={50} outerRadius={90}>{d.by_segment.map((_: any, i: number) => <Cell key={i} fill={COLORS[i]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer></div></Card>
    </div>
    <Card title="Monthly volume (EGP millions)"><div className="h-64"><ResponsiveContainer>
      <LineChart data={monthly}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="month" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Legend /><Line dataKey="credit" stroke="#0f8a6a" strokeWidth={2} /><Line dataKey="debit" stroke="#c8962e" strokeWidth={2} /></LineChart>
    </ResponsiveContainer></div></Card>
  </>);
}

function Fraud({ lang, canTriage }: { lang: string; canTriage: boolean }) {
  const [d, setD] = useState<any>(null);
  const [feed, setFeed] = useState<any[]>([]);
  const load = () => api("/staff/alerts").then(setD);
  useEffect(() => {
    load();
    const ws = new WebSocket(WS + "/ws/events");
    ws.onmessage = (m) => { const e = JSON.parse(m.data); if (e.type === "transaction") { setFeed((f) => [e, ...f].slice(0, 40)); if (e.flagged) load(); } };
    return () => ws.close();
  }, []);
  const triage = async (id: number, action: string) => { await api(`/staff/alerts/${id}`, { body: { action } }); load(); };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={<span>Live transaction stream <span className="chip ms-2 bg-emerald-100 text-emerald-700">● live</span></span>}>
        <div className="max-h-[560px] space-y-1 overflow-y-auto text-sm">
          {feed.map((e, i) => (
            <div key={i} className={`flex items-center justify-between rounded-lg px-2 py-1.5 ${e.flagged ? "bg-red-50 dark:bg-red-950/40" : ""}`}>
              <span><span className="muted">#{e.tx.customer_id}</span> {e.tx.merchant} <span className="muted">· {e.tx.channel} · {e.tx.governorate}</span></span>
              <span className="flex items-center gap-2"><b className="num">{egp(e.tx.amount, lang)}</b><span className={`chip ${e.risk_score >= 60 ? "bg-red-600 text-white" : e.risk_score >= 30 ? "bg-amber-100 text-amber-800" : "bg-slate-100 dark:bg-slate-800"}`}>{e.risk_score}</span></span>
            </div>))}
          {!feed.length && <div className="muted">Waiting for transactions…</div>}
        </div>
      </Card>
      <Card title="Alert queue">
        <div className="max-h-[560px] space-y-2 overflow-y-auto">
          {d?.alerts.map((a: any) => (
            <div key={a.id} className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-800">
              <div className="flex items-center justify-between"><b>{a.title}</b><span className={`chip ${a.risk_score >= 80 ? "bg-red-600 text-white" : "bg-amber-100 text-amber-800"}`}>{a.kind} · {a.risk_score}</span></div>
              <div className="text-xs muted">{JSON.parse(a.reasons || "[]").join(" · ")}</div>
              <div className="mt-2 flex items-center gap-2 text-xs"><span className="chip bg-slate-100 dark:bg-slate-800">{a.status}</span>
                {canTriage && a.status === "open" && <><button className="btn-ghost !py-0.5 text-xs" onClick={() => triage(a.id, "dismiss")}>False positive</button><button className="btn-primary !bg-red-600 !py-0.5 text-xs" onClick={() => triage(a.id, "escalate")}>Escalate case</button></>}</div>
            </div>))}
        </div>
      </Card>
    </div>
  );
}

function C360({ lang, canReveal }: { lang: string; canReveal: boolean }) {
  const [q, setQ] = useState("Mohamed");
  const [list, setList] = useState<any[]>([]);
  const [c, setC] = useState<any>(null);
  const [pii, setPii] = useState<any>(null);
  const search = () => api(`/staff/customers?q=${encodeURIComponent(q)}`).then(setList);
  useEffect(() => { search(); }, []);
  const open = (id: number) => { setPii(null); api(`/staff/customers/${id}`).then(setC); };
  const reveal = async () => { const reason = prompt("Justification (audited):", "Fraud investigation case #"); if (reason) setPii(await api(`/staff/customers/${c.customer.customer_id}/reveal`, { body: { reason } }).catch((e) => ({ error: String(e.detail) }))); };
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="Search">
        <form onSubmit={(e) => { e.preventDefault(); search(); }} className="flex gap-2"><input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="name / CIF / id" /><button className="btn-primary">Go</button></form>
        <ul className="mt-3 max-h-[480px] space-y-1 overflow-y-auto text-sm">{list.map((r) => (
          <li key={r.customer_id}><button className="w-full rounded-lg px-2 py-1.5 text-start hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => open(r.customer_id)}>
            <b>{lang === "ar" ? r.full_name_ar : r.full_name_en}</b><div className="text-xs muted">{r.cif} · {r.governorate_en} · {r.segment} · AML {r.aml_risk}</div></button></li>))}</ul>
      </Card>
      {c && (
        <Card className="lg:col-span-2" title={`${c.customer.full_name_en} · ${c.customer.full_name_ar}`} right={canReveal && <button className="btn-ghost text-xs" onClick={reveal}>🔓 Break-glass PII</button>}>
          <div className="grid gap-2 text-sm md:grid-cols-3">
            {["cif", "national_id", "phone", "email", "age", "gender", "governorate_en", "city", "occupation_en", "monthly_income", "segment", "kyc_status", "aml_risk", "credit_score", "customer_since"].map((k) => (
              <div key={k}><div className="text-xs muted">{k}</div><div className="num">{String(c.customer[k]).slice(0, 24)}</div></div>))}
          </div>
          {pii && <div className="mt-3 rounded-xl bg-amber-50 p-3 text-sm dark:bg-amber-950/40">{pii.error || `Unmasked (audited): NID ${pii.national_id} · ${pii.phone} · ${pii.email}`}</div>}
          <div className="mt-3 text-xs muted">Profile views by you in the last hour: {c.views_last_hour} (UEBA alert at 15+)</div>
          <table className="mt-3 w-full text-sm"><tbody>{c.recent_transactions.map((r: any, i: number) => (
            <tr key={i} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1 muted num">{String(r.ts).slice(0, 10)}</td><td>{r.merchant}</td><td className="muted">{r.channel}</td><td className="text-end num">{r.direction === "credit" ? "+" : "−"}{egp(r.amount, lang)}</td></tr>))}</tbody></table>
        </Card>)}
    </div>
  );
}

function Gov() {
  const [d, setD] = useState<any>(null);
  useEffect(() => { api("/staff/governance").then(setD); }, []);
  if (!d) return <div className="muted">Loading…</div>;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Data catalog & classification">
        <table className="w-full text-sm"><tbody>{d.catalog.map((c: any, i: number) => (
          <tr key={i} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1.5"><b>{c.table}</b>.<span className="muted">{c.columns}</span></td>
            <td><span className={`chip ${c.classification.startsWith("PII") ? "bg-red-100 text-red-700" : c.classification.startsWith("Sensitive") || c.classification.startsWith("PCI") ? "bg-amber-100 text-amber-800" : "bg-slate-100 dark:bg-slate-800"}`}>{c.classification}</span></td>
            <td className="text-xs muted">{c.control}</td></tr>))}</tbody></table>
      </Card>
      <Card title={`Data-quality checks (${d.dq.filter((x: any) => x.status === "PASS").length}/${d.dq.length} pass)`}>
        <table className="w-full text-sm"><tbody>{d.dq.map((c: any) => (
          <tr key={c.check} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1.5">{c.check}</td><td className="muted text-xs">{c.dimension}</td><td className="num text-xs">{c.failed}/{c.total.toLocaleString()}</td>
            <td><span className={`chip ${c.status === "PASS" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>{c.status}</span></td></tr>))}</tbody></table>
      </Card>
      <Card title={<span>Audit log <span className={`chip ms-2 ${d.audit_chain.intact ? "bg-emerald-100 text-emerald-700" : "bg-red-600 text-white"}`}>{d.audit_chain.intact ? `✓ hash chain intact (${d.audit_chain.entries})` : `✗ tampered at #${d.audit_chain.broken_at}`}</span></span>}>
        <div className="max-h-96 overflow-y-auto"><table className="w-full text-xs"><tbody>{d.audit_recent.map((a: any) => (
          <tr key={a.id} className="border-t border-slate-100 dark:border-slate-800"><td className="py-1 num muted">{a.ts.slice(11, 19)}</td><td>{a.actor}</td><td><b>{a.action}</b></td><td className="muted">{a.target}</td><td className="num muted">{a.hash}</td></tr>))}</tbody></table></div>
      </Card>
      <Card title="Privacy, retention & regulation">
        <div className="text-sm">Consents: {d.consents.users || 0} users · AI assistant {d.consents.ai || 0} · marketing {d.consents.marketing || 0}</div>
        <ul className="mt-2 space-y-1 text-sm">{d.retention.map((r: any) => <li key={r.data}>• <b>{r.data}</b>: {r.policy}</li>)}</ul>
        <ul className="mt-3 space-y-1 text-xs muted">{d.regulation.map((r: string) => <li key={r}>§ {r}</li>)}</ul>
      </Card>
    </div>
  );
}

function Models({ lang }: { lang: string }) {
  const [d, setD] = useState<any>(null);
  useEffect(() => { api("/staff/models").then(setD); }, []);
  if (!d) return <div className="muted">Loading…</div>;
  const f = d.forecast, fr = d.fraud;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Stock forecasting — walk-forward validation">
        <div className="text-xs muted">{f.model}<br />{f.validation} · data: {f.data_source.join(", ")}</div>
        <div className="mt-3 h-60"><ResponsiveContainer><BarChart data={f.folds}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="test_from" fontSize={10} /><YAxis domain={[0.4, 0.6]} fontSize={10} /><Tooltip /><Legend />
          <Bar dataKey="model_acc" name="LightGBM" fill="#0f8a6a" /><Bar dataKey="always_up_acc" name="Always up" fill="#94a3b8" /><Bar dataKey="momentum_acc" name="Momentum" fill="#c8962e" /></BarChart></ResponsiveContainer></div>
        <div className="mt-2 text-sm">Shuffled-label leak test: <b>{pct(f.shuffled_label_acc, lang)}</b> (should be ≈50%)</div>
        <div className="mt-1 text-xs muted">{f.note}</div>
      </Card>
      <Card title="Fraud detection — holdout">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><div className="muted">PR-AUC LightGBM</div><b className="text-2xl num">{fr.pr_auc_lightgbm}</b></div>
          <div><div className="muted">PR-AUC IsolationForest</div><b className="text-2xl num">{fr.pr_auc_isolation_forest}</b></div>
          <div><div className="muted">Precision @0.5</div><b className="num">{fr.precision_at_0_5 ?? fr["precision_at_0.5"]}</b></div>
          <div><div className="muted">Recall @0.5</div><b className="num">{fr["recall_at_0.5"]}</b></div>
        </div>
        <div className="mt-3 text-sm">Scenarios: {Object.entries(fr.scenarios).map(([k, v]) => `${k} (${v})`).join(" · ")}</div>
        <div className="mt-2 text-xs muted">Near-perfect scores reflect clearly-separable synthetic fraud. Real-world fraud needs real labels, drift monitoring and a fixed alert budget.</div>
      </Card>
    </div>
  );
}

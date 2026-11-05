"use client";
import { useEffect, useState } from "react";
import { api, egp } from "@/lib/api";
import { useApp } from "@/lib/i18n";
import { Card } from "@/components/ui";

export default function Security() {
  const { t, lang } = useApp();
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const load = () => api("/me/security").then(setD);
  useEffect(() => { load(); }, []);
  async function sim() { setBusy(true); await api("/demo/suspicious-transaction", { method: "POST" }); await load(); setBusy(false); }
  async function respond(id: number, action: string) { await api(`/me/alerts/${id}`, { body: { action } }); load(); }
  if (!d) return <div className="muted">Loading…</div>;
  return (
    <div className="space-y-5">
      <Card title={t("alerts")} right={<button className="btn-primary !bg-red-600" disabled={busy} onClick={sim}>⚡ {t("simulate")}</button>}>
        <div className="space-y-3">
          {d.alerts.map((a: any) => (
            <div key={a.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
              <span className={`chip ${a.risk_score >= 80 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"}`}>{a.kind} · {a.risk_score}</span>
              <div className="flex-1"><b className="text-sm">{a.title}</b><div className="text-xs muted">{JSON.parse(a.reasons || "[]").join(" · ")} · {a.ts.slice(0, 19).replace("T", " ")}</div></div>
              {a.status === "open" ? (<>
                <button className="btn-ghost !py-1 text-xs" onClick={() => respond(a.id, "confirm")}>{t("itWasMe")}</button>
                <button className="btn-primary !bg-red-600 !py-1 text-xs" onClick={() => respond(a.id, "fraud")}>{t("notMe")}</button></>)
                : <span className="chip bg-slate-100 dark:bg-slate-800">{a.status}</span>}
            </div>))}
          {!d.alerts.length && <div className="muted text-sm">{lang === "ar" ? "لا توجد تنبيهات" : "No alerts — all good."}</div>}
        </div>
      </Card>
      <Card title={t("logins")}>
        <table className="w-full text-sm"><tbody>{d.logins.map((l: any, i: number) => (
          <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
            <td className="py-2 num muted">{l.ts.slice(0, 19).replace("T", " ")}</td><td className="num">{l.ip}</td>
            <td className="max-w-xs truncate muted">{l.user_agent}</td>
            <td>{l.success ? "✅" : "❌"}</td>
            <td><span className={`chip ${l.risk_score >= 40 ? "bg-red-100 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>risk {l.risk_score}</span> <span className="text-xs muted">{JSON.parse(l.reasons || "[]").join(", ")}</span></td>
          </tr>))}</tbody></table>
      </Card>
    </div>
  );
}

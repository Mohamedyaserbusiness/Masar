"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AuthFrame from "@/components/AuthFrame";
import { api } from "@/lib/api";
import { useApp } from "@/lib/i18n";

const DEMO = [["demo@masar.eg", "Customer"], ["advisor@masar.eg", "Advisor"], ["compliance@masar.eg", "Compliance"], ["admin@masar.eg", "Admin"]];

export default function Login() {
  const { t } = useApp();
  const router = useRouter();
  const [email, setEmail] = useState("demo@masar.eg");
  const [password, setPassword] = useState("Masar@2026");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const r = await api<{ role: string; login_risk: { risk_score: number } }>("/auth/login", { body: { email, password } });
      router.replace(r.role === "customer" ? "/dashboard" : "/staff");
    } catch (e: any) { setErr(String(e.detail || e.message)); } finally { setBusy(false); }
  }
  return (
    <AuthFrame>
      <h2 className="text-2xl font-bold">{t("signin")}</h2>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <div><label className="label">{t("email")}</label><input className="input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div><label className="label">{t("password")}</label><input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
        {err && <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{err}</div>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "…" : t("signin")}</button>
      </form>
      <div className="mt-6 card !p-4">
        <div className="label">{t("demoAccounts")} · Masar@2026</div>
        <div className="flex flex-wrap gap-2">{DEMO.map(([e, r]) => <button key={e} className="btn-ghost !py-1 text-xs" onClick={() => { setEmail(e); setPassword("Masar@2026"); }}>{r}</button>)}</div>
      </div>
      <p className="mt-4 text-sm muted">{t("noAccount")} <Link className="font-semibold text-brand-600" href="/signup">{t("signup")}</Link></p>
    </AuthFrame>
  );
}

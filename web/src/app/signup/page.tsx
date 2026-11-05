"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AuthFrame from "@/components/AuthFrame";
import { api } from "@/lib/api";
import { useApp } from "@/lib/i18n";

export default function Signup() {
  const { t } = useApp();
  const router = useRouter();
  const [f, setF] = useState({ full_name: "", email: "", phone: "", national_id: "", password: "", consent_data: false, consent_ai: true, consent_marketing: false });
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErrs({});
    try { await api("/auth/signup", { body: f }); router.replace("/dashboard"); }
    catch (e: any) { setErrs(typeof e.detail === "object" ? e.detail : { form: String(e.detail) }); }
    finally { setBusy(false); }
  }
  const field = (k: keyof typeof f, label: string, type = "text", ph = "") => (
    <div>
      <label className="label">{label}</label>
      <input className="input" type={type} placeholder={ph} value={f[k] as string} onChange={(e) => set(k, e.target.value)} />
      {errs[k] && <div className="mt-1 text-xs text-red-600">{errs[k]}</div>}
    </div>
  );
  return (
    <AuthFrame>
      <h2 className="text-2xl font-bold">{t("signup")}</h2>
      <form onSubmit={submit} className="mt-6 space-y-3">
        {field("full_name", t("fullName"), "text", "Ahmed Mohamed Hassan")}
        {field("email", t("email"), "email", "name@example.com")}
        <div className="grid grid-cols-2 gap-3">{field("phone", t("phone"), "tel", "01012345678")}{field("national_id", t("nationalId"), "text", "29501120100503")}</div>
        {field("password", t("password"), "password", "8+ chars, Aa1")}
        {[["consent_data", t("consentData")], ["consent_ai", t("consentAi")], ["consent_marketing", t("consentMkt")]].map(([k, l]) => (
          <label key={k} className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={(f as any)[k]} onChange={(e) => set(k, e.target.checked)} />{l}</label>
        ))}
        {errs.consent_data && <div className="text-xs text-red-600">{errs.consent_data}</div>}
        {errs.form && <div className="text-sm text-red-600">{errs.form}</div>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "…" : t("signup")}</button>
      </form>
      <p className="mt-4 text-sm muted">{t("haveAccount")} <Link className="font-semibold text-brand-600" href="/login">{t("signin")}</Link></p>
    </AuthFrame>
  );
}

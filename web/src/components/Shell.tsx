"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { Bot, Building2, Eye, EyeOff, Home, LineChart, LogOut, Moon, PieChart, ShieldCheck, Sun } from "lucide-react";
import { api } from "@/lib/api";
import { Key, useApp } from "@/lib/i18n";

export type Me = { id: number; email: string; role: string; customer_id: number | null; full_name: string; risk_band: number | null };
const MeCtx = createContext<Me | null>(null);
export const useMe = () => useContext(MeCtx);

const NAV: { href: string; key: Key; icon: any; roles: string[] }[] = [
  { href: "/dashboard", key: "dashboard", icon: Home, roles: ["customer"] },
  { href: "/markets", key: "markets", icon: LineChart, roles: ["customer", "advisor", "compliance", "admin"] },
  { href: "/invest", key: "invest", icon: PieChart, roles: ["customer"] },
  { href: "/assistant", key: "assistant", icon: Bot, roles: ["customer"] },
  { href: "/security", key: "security", icon: ShieldCheck, roles: ["customer"] },
  { href: "/staff", key: "staff", icon: Building2, roles: ["advisor", "compliance", "admin"] },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang, dark, setDark, privacy, setPrivacy } = useApp();
  const [me, setMe] = useState<Me | null>(null);
  const path = usePathname();
  const router = useRouter();
  useEffect(() => {
    api<Me>("/auth/me").then(setMe).catch(() => router.replace("/login"));
  }, [router]);
  if (!me) return <div className="grid min-h-screen place-items-center muted">Loading…</div>;
  const nav = NAV.filter((n) => n.roles.includes(me.role));
  return (
    <MeCtx.Provider value={me}>
      <div className="min-h-screen md:flex">
        <aside className="border-slate-200 bg-white md:sticky md:top-0 md:h-screen md:w-60 md:border-e dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-2 px-5 py-5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-lg font-bold text-white">م</div>
            <div><div className="font-bold leading-tight">{t("brand")}</div><div className="text-xs muted">{t("tagline")}</div></div>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col">
            {nav.map((n) => (
              <Link key={n.href} href={n.href}
                className={`flex shrink-0 items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium ${path.startsWith(n.href) ? "bg-brand-50 text-brand-700 dark:bg-brand-700/20 dark:text-brand-100" : "hover:bg-slate-100 dark:hover:bg-slate-800"}`}>
                <n.icon size={18} /> {t(n.key)}
              </Link>
            ))}
          </nav>
        </aside>
        <main className="flex-1">
          <header className="sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-slate-200 bg-white/80 px-5 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
            <div className="text-sm"><span className="muted">{t("hi")}, </span><b>{me.full_name}</b> <span className="chip ms-2 bg-slate-100 dark:bg-slate-800">{me.role}</span></div>
            <div className="flex items-center gap-1">
              <button className="btn-ghost !px-3" onClick={() => setPrivacy(!privacy)} title={t("hidden")}>{privacy ? <EyeOff size={16} /> : <Eye size={16} />}</button>
              <button className="btn-ghost !px-3" onClick={() => setDark(!dark)}>{dark ? <Sun size={16} /> : <Moon size={16} />}</button>
              <button className="btn-ghost !px-3" onClick={() => setLang(lang === "en" ? "ar" : "en")}>{lang === "en" ? "عربي" : "EN"}</button>
              <button className="btn-ghost !px-3" onClick={async () => { await api("/auth/logout", { method: "POST" }).catch(() => {}); router.replace("/login"); }}><LogOut size={16} /></button>
            </div>
          </header>
          <div className="mx-auto max-w-7xl p-4 md:p-6">{children}</div>
        </main>
      </div>
    </MeCtx.Provider>
  );
}

"use client";
export const COLORS = ["#0f8a6a", "#c8962e", "#3b82f6", "#a855f7", "#ef4444", "#14b8a6", "#f59e0b", "#64748b", "#ec4899", "#22c55e", "#0ea5e9", "#8b5cf6", "#f97316"];

export function Stat({ label, value, sub, sensitive = true, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; sensitive?: boolean; tone?: "up" | "down" }) {
  return (
    <div className="card">
      <div className="text-xs font-semibold muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold num ${sensitive ? "sensitive" : ""} ${tone === "up" ? "text-emerald-600" : tone === "down" ? "text-red-600" : ""}`}>{value}</div>
      {sub && <div className="mt-1 text-xs muted">{sub}</div>}
    </div>
  );
}

export function Card({ title, children, right, className = "" }: { title?: React.ReactNode; children: React.ReactNode; right?: React.ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || right) && <div className="mb-3 flex items-center justify-between gap-2"><h3 className="font-semibold">{title}</h3>{right}</div>}
      {children}
    </section>
  );
}

export function SourceBadge({ source }: { source?: string }) {
  const live = source?.startsWith("LIVE") || source === "TWELVE DATA";
  return <span className={`chip ${live ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"}`}>{live ? "● " : "◌ "}{source || "SIMULATED"}</span>;
}

export function Change({ v }: { v: number }) {
  const up = v >= 0;
  return <span className={`num font-semibold ${up ? "text-emerald-600" : "text-red-600"}`}>{up ? "▲" : "▼"} {Math.abs(v).toFixed(2)}%</span>;
}

export function Gauge({ value }: { value: number }) {
  const color = value >= 70 ? "#0f8a6a" : value >= 45 ? "#c8962e" : "#ef4444";
  return (
    <div className="relative mx-auto h-24 w-24">
      <svg viewBox="0 0 36 36" className="h-24 w-24 -rotate-90">
        <circle cx="18" cy="18" r="15.9" fill="none" stroke="currentColor" className="text-slate-200 dark:text-slate-800" strokeWidth="3.5" />
        <circle cx="18" cy="18" r="15.9" fill="none" stroke={color} strokeWidth="3.5" strokeDasharray={`${value} 100`} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-xl font-bold num">{value}</div>
    </div>
  );
}

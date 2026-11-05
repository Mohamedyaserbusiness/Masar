export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS = API.replace(/^http/, "ws");

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : "Request failed");
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(API + path, {
    method: opts.method || (opts.body ? "POST" : "GET"),
    credentials: "include",
    headers: { "content-type": "application/json", "x-requested-with": "masar" },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let d: any = res.statusText;
    try { d = (await res.json()).detail; } catch {}
    throw new ApiError(res.status, d);
  }
  return res.json();
}

export const egp = (n: number | null | undefined, lang = "en", digits = 0) =>
  n == null ? "—" : new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-EG", { style: "currency", currency: "EGP", maximumFractionDigits: digits }).format(n);

export const num = (n: number | null | undefined, lang = "en", digits = 2) =>
  n == null ? "—" : new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);

export const pct = (n: number | null | undefined, lang = "en", digits = 1) =>
  n == null ? "—" : new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US", { style: "percent", maximumFractionDigits: digits }).format(n);

"use client";
import { useApp } from "@/lib/i18n";

export default function AuthFrame({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useApp();
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="hidden flex-col justify-between bg-gradient-to-br from-brand-700 via-brand-600 to-emerald-500 p-10 text-white md:flex">
        <div className="flex items-center gap-2 text-xl font-bold"><span className="grid h-10 w-10 place-items-center rounded-xl bg-white/20">م</span>{t("brand")}</div>
        <div>
          <h1 className="text-4xl font-bold leading-tight">{lang === "ar" ? "فلوسك، استثماراتك، وأمانك — في مكان واحد." : "Your money, your investments and your security — in one place."}</h1>
          <ul className="mt-6 space-y-2 text-white/90">
            {(lang === "ar"
              ? ["بورصة مصر وأمريكا مباشر", "توصيات أسهم حسب ملف المخاطر", "كشف الاحتيال لحظياً", "مساعد ذكي Llama يعمل محلياً — بياناتك لا تغادر مصر"]
              : ["Live EGX & US markets", "Stock picks matched to your risk profile", "Real-time fraud detection", "Local Llama assistant — your data never leaves Egypt"]
            ).map((x) => <li key={x}>✓ {x}</li>)}
          </ul>
        </div>
        <div className="text-xs text-white/70">Demo edition · synthetic data · 2026</div>
      </div>
      <div className="relative grid place-items-center p-6">
        <button className="btn-ghost absolute end-4 top-4" onClick={() => setLang(lang === "en" ? "ar" : "en")}>{lang === "en" ? "عربي" : "EN"}</button>
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}

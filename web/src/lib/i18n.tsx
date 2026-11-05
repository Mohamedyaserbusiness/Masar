"use client";
import { createContext, useContext, useEffect, useState } from "react";

const dict = {
  en: {
    brand: "Masar", tagline: "Smart banking for Egypt", dashboard: "Home", markets: "Live markets", invest: "Invest", assistant: "Assistant",
    security: "Security", staff: "Staff console", logout: "Sign out", signin: "Sign in", signup: "Create account", email: "Email",
    password: "Password", fullName: "Full name", phone: "Mobile number", nationalId: "National ID (14 digits)",
    totalBalance: "Total balance", income: "Monthly income", spend: "Monthly spending", savingsRate: "Savings rate", netWorth: "Net worth",
    health: "Financial health", accounts: "Accounts", cards: "Cards", loans: "Loans", cds: "Certificates", recent: "Recent transactions",
    spendByCat: "Spending by category (90 days)", incomeVsSpend: "Income vs spending", dailySpend: "Daily spending (60 days)",
    topMerchants: "Top merchants", subscriptions: "Detected subscriptions & bills", peers: "You vs similar customers (monthly)",
    you: "You", peersL: "Peers", hi: "Welcome back", demoAccounts: "Demo accounts", noAccount: "No account?", haveAccount: "Already registered?",
    wasThisYou: "Was this you?", itWasMe: "Yes, it was me", notMe: "No — freeze my card", liveFeed: "Live", simulated: "SIMULATED",
    open: "Open", closed: "Closed", forecast: "AI forecast (5 days)", probUp: "Chance of up day", expRet: "Expected 5-day return",
    range: "80% range", confidence: "Confidence", modelHonesty: "Model honesty check", riskQuiz: "Your risk profile", recommendations: "Recommended for you",
    allocation: "Suggested allocation", why: "Why", shariaOnly: "Sharia-compliant only", disclaimer: "Educational only — not investment advice.",
    ask: "Ask anything about your money…", send: "Send", logins: "Sign-in history", alerts: "Security alerts", simulate: "Simulate suspicious transaction",
    overview: "Overview", fraud: "Fraud monitor", customer360: "Customer 360", governance: "Data governance", models: "Models",
    hidden: "Hide balances", consentData: "I agree to the processing of my personal data (PDPL, required)", consentAi: "Allow the AI assistant to read my account data",
    consentMkt: "Send me offers (optional)",
  },
  ar: {
    brand: "مسار", tagline: "بنك ذكي لمصر", dashboard: "الرئيسية", markets: "البورصة مباشر", invest: "استثمر", assistant: "المساعد الذكي",
    security: "الأمان", staff: "لوحة الموظفين", logout: "تسجيل الخروج", signin: "تسجيل الدخول", signup: "إنشاء حساب", email: "البريد الإلكتروني",
    password: "كلمة المرور", fullName: "الاسم بالكامل", phone: "رقم الموبايل", nationalId: "الرقم القومي (14 رقم)",
    totalBalance: "إجمالي الرصيد", income: "الدخل الشهري", spend: "المصروف الشهري", savingsRate: "نسبة الادخار", netWorth: "صافي الثروة",
    health: "الصحة المالية", accounts: "الحسابات", cards: "الكروت", loans: "القروض", cds: "الشهادات", recent: "آخر المعاملات",
    spendByCat: "المصروفات حسب الفئة (90 يوم)", incomeVsSpend: "الدخل مقابل المصروف", dailySpend: "المصروف اليومي (60 يوم)",
    topMerchants: "أكثر التجار", subscriptions: "الاشتراكات والفواتير المكتشفة", peers: "مقارنتك بعملاء مشابهين (شهرياً)",
    you: "أنت", peersL: "المشابهين", hi: "أهلاً بيك", demoAccounts: "حسابات تجريبية", noAccount: "معندكش حساب؟", haveAccount: "عندك حساب؟",
    wasThisYou: "هل قمت بهذه العملية؟", itWasMe: "أيوه، دي أنا", notMe: "لأ — جمّد الكارت", liveFeed: "مباشر", simulated: "محاكاة",
    open: "مفتوحة", closed: "مغلقة", forecast: "توقع الذكاء الاصطناعي (5 أيام)", probUp: "احتمال الصعود", expRet: "العائد المتوقع (5 أيام)",
    range: "نطاق 80%", confidence: "الثقة", modelHonesty: "اختبار مصداقية النموذج", riskQuiz: "ملف المخاطر الخاص بك", recommendations: "مقترحات مناسبة لك",
    allocation: "التوزيع المقترح", why: "ليه", shariaOnly: "متوافق مع الشريعة فقط", disclaimer: "معلومات تعليمية — ليست نصيحة استثمارية.",
    ask: "اسأل أي سؤال عن فلوسك…", send: "إرسال", logins: "سجل الدخول", alerts: "تنبيهات الأمان", simulate: "محاكاة عملية مشبوهة",
    overview: "نظرة عامة", fraud: "مراقبة الاحتيال", customer360: "ملف العميل 360", governance: "حوكمة البيانات", models: "النماذج",
    hidden: "إخفاء الأرصدة", consentData: "أوافق على معالجة بياناتي الشخصية (قانون حماية البيانات - إجباري)", consentAi: "السماح للمساعد الذكي بقراءة بيانات حسابي",
    consentMkt: "أرسلوا لي العروض (اختياري)",
  },
};
export type Key = keyof typeof dict.en;
type Ctx = { lang: "en" | "ar"; setLang: (l: "en" | "ar") => void; t: (k: Key) => string; dark: boolean; setDark: (d: boolean) => void; privacy: boolean; setPrivacy: (p: boolean) => void };
const C = createContext<Ctx>(null as any);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<"en" | "ar">("en");
  const [dark, setDark] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  useEffect(() => {
    try {
      const l = localStorage.getItem("lang"); if (l === "ar" || l === "en") setLang(l);
      setDark(localStorage.getItem("dark") === "1");
    } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.classList.toggle("privacy", privacy);
    try { localStorage.setItem("lang", lang); localStorage.setItem("dark", dark ? "1" : "0"); } catch {}
  }, [lang, dark, privacy]);
  return <C.Provider value={{ lang, setLang, t: (k) => dict[lang][k] ?? k, dark, setDark, privacy, setPrivacy }}>{children}</C.Provider>;
}
export const useApp = () => useContext(C);

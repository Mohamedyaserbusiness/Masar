"use client";
import { useRef, useState } from "react";
import { Bot, Send, User } from "lucide-react";
import { API } from "@/lib/api";
import { useApp } from "@/lib/i18n";

const SUGG = {
  en: ["What's my balance?", "How much did I spend on food last month?", "Recommend stocks for me", "What's the forecast for COMI?", "Any security alerts on my account?", "Gold price today?"],
  ar: ["كام رصيدي؟", "كم صرفت على الأكل الشهر اللي فات؟", "انصحني بأسهم مناسبة ليا", "إيه توقعات سهم التجاري الدولي COMI؟", "فيه أي تنبيهات أمان على حسابي؟", "سعر الذهب النهارده؟"],
};

type Msg = { role: "user" | "bot"; text: string; intent?: string };

export default function Assistant() {
  const { t, lang } = useApp();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  async function send(text: string) {
    if (!text.trim() || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", text }, { role: "bot", text: "" }]);
    try {
      const res = await fetch(API + "/chat", { method: "POST", credentials: "include", headers: { "content-type": "application/json", "x-requested-with": "masar" }, body: JSON.stringify({ message: text }) });
      const reader = res.body!.getReader(); const dec = new TextDecoder();
      let acc = "";
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        acc += dec.decode(value, { stream: true });
        const mm = acc.match(/^\[\[intent:(\w+)\]\]/);
        const intent = mm?.[1]; const body = acc.replace(/^\[\[intent:\w+\]\]/, "");
        setMsgs((m) => [...m.slice(0, -1), { role: "bot", text: body, intent }]);
        end.current?.scrollIntoView({ behavior: "smooth" });
      }
    } catch { setMsgs((m) => [...m.slice(0, -1), { role: "bot", text: "⚠ connection error" }]); }
    setBusy(false);
  }
  return (
    <div className="card flex h-[calc(100vh-9rem)] flex-col !p-0">
      <div className="flex items-center gap-3 border-b border-slate-200 p-4 dark:border-slate-800">
        <div className="grid h-10 w-10 place-items-center rounded-full bg-brand-600 text-white"><Bot size={20} /></div>
        <div><b>{t("assistant")}</b><div className="text-xs muted">Llama 3.2 · {lang === "ar" ? "يعمل محلياً — بياناتك لا تغادر الجهاز" : "runs locally — your data never leaves this server"}</div></div>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {!msgs.length && (
          <div className="mx-auto max-w-xl pt-8 text-center">
            <div className="text-lg font-semibold">{lang === "ar" ? "أهلاً! أقدر أساعدك في إيه؟" : "Hi! How can I help with your money today?"}</div>
            <div className="mt-4 flex flex-wrap justify-center gap-2">{SUGG[lang].map((s) => <button key={s} className="btn-ghost !py-1.5 text-xs" onClick={() => send(s)}>{s}</button>)}</div>
          </div>)}
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${m.role === "user" ? "bg-slate-200 dark:bg-slate-700" : "bg-brand-100 text-brand-700"}`}>{m.role === "user" ? <User size={16} /> : <Bot size={16} />}</div>
            <div className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${m.role === "user" ? "bg-brand-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`}>
              {m.text || <span className="animate-pulse">…</span>}
              {m.intent && <div className="mt-1 text-[10px] opacity-60">tool: {m.intent}</div>}
            </div>
          </div>))}
        <div ref={end} />
      </div>
      <form className="flex gap-2 border-t border-slate-200 p-3 dark:border-slate-800" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder={t("ask")} />
        <button className="btn-primary" disabled={busy}><Send size={16} /></button>
      </form>
    </div>
  );
}

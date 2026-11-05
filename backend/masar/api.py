"""Masar API (FastAPI). Run: uvicorn masar.api:app --port 8000"""
from __future__ import annotations

import asyncio
import json
import random
from contextlib import asynccontextmanager
from datetime import timedelta

import duckdb
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import chat, egypt as E, recommend as R, security as S, store
from .config import AS_OF, COOKIE_NAME, DEMO_PASSWORD, DUCKDB_PATH, JWT_HOURS, MODELS_DIR, OLLAMA_MODEL, OLLAMA_URL, WEB_ORIGINS
from .live import events, hub, market_status

_db = duckdb.connect(str(DUCKDB_PATH), read_only=True)


def db(sql: str, args=None) -> list[dict]:
    cur = _db.cursor()
    res = cur.execute(sql, args or [])
    cols = [d[0] for d in res.description]
    return [dict(zip(cols, r)) for r in res.fetchall()]


def seed_users():
    demo = db("SELECT demo_customer_id d FROM demo_meta")[0]["d"]
    name = db("SELECT full_name_en FROM customers WHERE customer_id=?", [demo])[0]["full_name_en"]
    for email, role, cid, nm in [("demo@masar.eg", "customer", demo, name), ("advisor@masar.eg", "advisor", None, "Rana Advisor"),
                                 ("compliance@masar.eg", "compliance", None, "Karim Compliance"), ("admin@masar.eg", "admin", None, "Admin")]:
        if not store.q("SELECT 1 FROM users WHERE email=?", (email,)):
            store.x("INSERT INTO users(email,password_hash,role,customer_id,full_name,created_at) VALUES(?,?,?,?,?,?)",
                    (email, S.hash_pw(DEMO_PASSWORD), role, cid, nm, store.now()))


async def warm_llm():
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            await c.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "prompt": "hi", "keep_alive": "30m", "options": {"num_predict": 1}})
    except Exception as e:
        print("LLM warm-up failed:", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_users(); hub.load(); events.load()
    tasks = [asyncio.create_task(hub.simulate_loop()), asyncio.create_task(hub.finnhub_loop()),
             asyncio.create_task(events.loop()), asyncio.create_task(warm_llm())]
    store.audit("system", "system", "API_START")
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="Masar API", version="0.1-demo", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=WEB_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def headers(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.headers.get("x-requested-with") != "masar":
        return Response('{"detail":"CSRF check failed"}', status_code=403, media_type="application/json")
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"; resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.get("/health")
def health():
    return {"status": "ok", "customers": db("SELECT COUNT(*) n FROM customers")[0]["n"], "market": market_status()}


# ------------------------------- auth -------------------------------

class Signup(BaseModel):
    full_name: str; email: str; phone: str; national_id: str; password: str
    consent_data: bool; consent_ai: bool = True; consent_marketing: bool = False


class Login(BaseModel):
    email: str; password: str


def _set_cookie(resp: Response, user: dict):
    resp.set_cookie(COOKIE_NAME, S.make_token(user), httponly=True, samesite="lax", max_age=JWT_HOURS * 3600, path="/")


@app.post("/auth/signup")
def signup(body: Signup, request: Request, response: Response):
    S.rate_limit(request.client.host)
    errs = {}
    ok, msg = E.validate_national_id(body.national_id)
    if not ok: errs["national_id"] = msg
    if not E.validate_phone(body.phone): errs["phone"] = "Egyptian mobile like 01012345678"
    if "@" not in body.email or "." not in body.email.split("@")[-1]: errs["email"] = "Invalid email"
    if (pw := S.password_issues(body.password)): errs["password"] = "Password needs " + ", ".join(pw)
    if not body.consent_data: errs["consent_data"] = "Consent to data processing is required (PDPL)"
    if store.q("SELECT 1 FROM users WHERE email=?", (body.email.lower(),)): errs["email"] = "Email already registered"
    if errs:
        raise HTTPException(422, errs)
    # link to existing synthetic customer by national ID, otherwise attach a sample history (demo onboarding)
    m = db("SELECT customer_id FROM customers WHERE national_id=?", [body.national_id])
    linked = bool(m)
    if m:
        cid = m[0]["customer_id"]
    else:
        dob, g = E.nid_birth_gender(body.national_id)
        age = (AS_OF - dob).days // 365
        cand = db("""SELECT customer_id FROM customers WHERE gender=? AND age BETWEEN ? AND ? AND digital_active AND governorate_code=?
                     USING SAMPLE 50 ROWS""", [g, age - 5, age + 5, body.national_id[7:9]]) or db("SELECT customer_id FROM customers USING SAMPLE 1 ROWS")
        cid = cand[0]["customer_id"]
    uid = store.x("INSERT INTO users(email,password_hash,role,customer_id,full_name,created_at) VALUES(?,?,?,?,?,?)",
                  (body.email.lower(), S.hash_pw(body.password), "customer", cid, body.full_name.strip(), store.now()))
    store.x("INSERT INTO consents VALUES(?,?,?,?,?)", (uid, 1, int(body.consent_ai), int(body.consent_marketing), store.now()))
    user = store.q("SELECT * FROM users WHERE id=?", (uid,))[0]
    S.record_login(user, user["email"], request.client.host, request.headers.get("user-agent", ""), True)
    store.audit(user["email"], "customer", "SIGNUP", f"customer:{cid}", {"linked_existing": linked})
    _set_cookie(response, user)
    return {"ok": True, "linked_existing_customer": linked}


@app.post("/auth/login")
def login(body: Login, request: Request, response: Response):
    S.rate_limit(request.client.host)
    email = body.email.lower().strip()
    rows = store.q("SELECT * FROM users WHERE email=?", (email,))
    ip, ua = request.client.host, request.headers.get("user-agent", "")
    user = rows[0] if rows else None
    if user and user["locked_until"] and user["locked_until"] > store.now():
        raise HTTPException(423, "Account temporarily locked after repeated failures. Try again in 5 minutes.")
    if not user or not S.verify_pw(user["password_hash"], body.password):
        S.record_login(user, email, ip, ua, False)
        if user:
            fails = user["failed_attempts"] + 1
            lock = (store.now() if fails < 5 else (__import__("datetime").datetime.now(__import__("datetime").timezone.utc) + timedelta(minutes=5)).isoformat())
            store.x("UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?", (fails, lock if fails >= 5 else None, user["id"]))
        store.audit(email, "anonymous", "LOGIN_FAILED")
        raise HTTPException(401, "Invalid email or password")
    store.x("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=?", (user["id"],))
    risk = S.record_login(user, email, ip, ua, True)
    store.audit(email, user["role"], "LOGIN", "", risk)
    _set_cookie(response, user)
    return {"ok": True, "role": user["role"], "login_risk": risk}


@app.post("/auth/logout")
def logout(response: Response, user=Depends(S.current_user)):
    store.audit(user["email"], user["role"], "LOGOUT")
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/auth/me")
def me(user=Depends(S.current_user)):
    rp = store.q("SELECT band FROM risk_profiles WHERE user_id=?", (user["id"],))
    return {**user, "risk_band": rp[0]["band"] if rp else None}


# ------------------------------- banking profile -------------------------------

def customer_of(user) -> int:
    if not user["customer_id"]:
        raise HTTPException(400, "This account has no banking profile (staff user)")
    return user["customer_id"]


def _profile(cid: int, unmask: bool = False) -> dict:
    c = db("SELECT * FROM customers WHERE customer_id=?", [cid])[0]
    if not unmask:
        c["national_id"] = E.mask_nid(c["national_id"]); c["phone"] = E.mask_phone(c["phone"]); c["email"] = E.mask_email(c["email"])
    acc = db("SELECT account_id,type,currency,balance,interest_rate,iban,status FROM accounts WHERE customer_id=?", [cid])
    for a in acc:
        a["iban"] = a["iban"] if unmask else E.mask_iban(a["iban"])
    return {"customer": c, "accounts": acc,
            "cards": db("SELECT card_type,last4,expiry,credit_limit,outstanding,status FROM cards WHERE customer_id=?", [cid]),
            "loans": db("SELECT * FROM loans WHERE customer_id=?", [cid]),
            "certificates": db("SELECT * FROM certificates WHERE customer_id=?", [cid]),
            "holdings": db("SELECT * FROM holdings WHERE customer_id=?", [cid])}


@app.get("/me/overview")
def overview(user=Depends(S.current_user)):
    cid = customer_of(user)
    p = _profile(cid)
    p["customer"]["display_name"] = user["full_name"]
    k = db("""SELECT SUM(CASE WHEN direction='credit' THEN amount END)/12 income, SUM(CASE WHEN direction='debit' THEN amount END)/12 spend
              FROM transactions WHERE customer_id=?""", [cid])[0]
    egp = sum(a["balance"] for a in p["accounts"] if a["currency"] == "EGP")
    usd = sum(a["balance"] for a in p["accounts"] if a["currency"] == "USD")
    total = egp + usd * hub.price.get("USD/EGP", 48.6)
    debt = sum(l["remaining"] for l in p["loans"]) + sum(c["outstanding"] for c in p["cards"])
    cds = sum(c["amount"] for c in p["certificates"])
    inv = sum(h["qty"] * hub.price.get(h["symbol"], h["avg_cost"]) * (hub.price.get("USD/EGP", 48.6) if h["symbol"] in {u[0] for u in E.US} else 1) for h in p["holdings"])
    income, spend = k["income"] or 0, k["spend"] or 0
    savings_rate = max(-1, (income - spend) / income) if income else 0
    em = (egp + cds) / spend if spend else 12
    inst = sum(l["monthly_installment"] for l in p["loans"])
    dti = inst / income if income else 0
    score = int(max(0, min(100, 35 * min(1, max(0, savings_rate) / 0.2) + 30 * min(1, em / 6) + 20 * (1 - min(1, dti / 0.5)) + 15 * (p["customer"]["credit_score"] - 400) / 450)))
    return {**p, "kpis": {"total_balance_egp": round(total, 2), "monthly_income": round(income, 2), "monthly_spend": round(spend, 2),
                          "savings_rate": round(savings_rate, 4), "net_worth": round(total + cds + inv - debt, 2), "investments": round(inv, 2),
                          "certificates": cds, "debt": round(debt, 2), "health_score": score, "emergency_months": round(em, 1), "dti": round(dti, 3)}}


@app.get("/me/transactions")
def my_transactions(limit: int = 30, user=Depends(S.current_user)):
    cid = customer_of(user)
    live = store.q("SELECT ts,amount,merchant,category,channel,governorate,risk_score,flagged FROM live_transactions WHERE customer_id=? ORDER BY id DESC LIMIT 10", (cid,))
    for t in live:
        t["direction"] = "debit"; t["live"] = True
    hist = db("SELECT ts,direction,amount,merchant,category,channel,governorate FROM transactions WHERE customer_id=? ORDER BY ts DESC LIMIT ?", [cid, min(limit, 200)])
    return live + hist


@app.get("/me/analytics")
def analytics(user=Depends(S.current_user)):
    cid = customer_of(user)
    c = db("SELECT segment, region FROM customers WHERE customer_id=?", [cid])[0]
    by_cat = db("""SELECT category, SUM(amount) amount, COUNT(*) n FROM transactions WHERE customer_id=? AND direction='debit'
                   AND ts >= ?::DATE - INTERVAL 90 DAY GROUP BY 1 ORDER BY 2 DESC""", [cid, AS_OF])
    monthly = db("""SELECT strftime(date_trunc('month', ts), '%Y-%m') AS "month", SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) income,
                    SUM(CASE WHEN direction='debit' THEN amount ELSE 0 END) spend FROM transactions WHERE customer_id=? GROUP BY 1 ORDER BY 1""", [cid])
    daily = db("""SELECT strftime(ts::DATE, '%m-%d') AS "day", SUM(amount) amount FROM transactions WHERE customer_id=? AND direction='debit'
                  AND ts >= ?::DATE - INTERVAL 60 DAY GROUP BY ts::DATE ORDER BY ts::DATE""", [cid, AS_OF])
    top = db("""SELECT merchant, SUM(amount) amount, COUNT(*) n FROM transactions WHERE customer_id=? AND direction='debit'
                AND ts >= ?::DATE - INTERVAL 90 DAY GROUP BY 1 ORDER BY 2 DESC LIMIT 6""", [cid, AS_OF])
    subs = db("""SELECT merchant, COUNT(DISTINCT date_trunc('month', ts)) AS n_months, AVG(amount) avg_amount FROM transactions
                 WHERE customer_id=? AND (category IN ('entertainment','telecom','utilities')) GROUP BY 1 HAVING COUNT(DISTINCT date_trunc('month', ts)) >= 3 ORDER BY avg_amount DESC""", [cid])
    peer = db("SELECT category, avg_monthly FROM peer_benchmark WHERE segment=? AND region=?", [c["segment"], c["region"]])
    mine = {r["category"]: r["amount"] / 3 for r in by_cat}
    bench = [{"category": p["category"], "label": E.CATEGORIES.get(p["category"], (p["category"],))[0], "you": round(mine.get(p["category"], 0), 2), "peers": round(p["avg_monthly"], 2)}
             for p in peer if p["category"] in mine]
    for r in by_cat:
        r["label"] = E.CATEGORIES.get(r["category"], (r["category"], r["category"]))[0]
        r["label_ar"] = E.CATEGORIES.get(r["category"], (r["category"], r["category"]))[1]
    return {"by_category_90d": by_cat, "monthly": monthly, "daily_60d": daily, "top_merchants_90d": top,
            "subscriptions": subs, "peer_benchmark": sorted(bench, key=lambda b: -b["you"])[:6], "segment": c["segment"], "region": c["region"]}


@app.get("/me/security")
def my_security(user=Depends(S.current_user)):
    return {"logins": store.q("SELECT ts,ip,user_agent,success,risk_score,reasons FROM login_events WHERE user_id=? ORDER BY id DESC LIMIT 20", (user["id"],)),
            "alerts": store.q("SELECT * FROM alerts WHERE customer_id=? ORDER BY id DESC LIMIT 20", (user["customer_id"] or -1,))}


class AlertAction(BaseModel):
    action: str        # "confirm" (it was me) | "fraud" (not me)


@app.post("/me/alerts/{aid}")
def respond_alert(aid: int, body: AlertAction, user=Depends(S.current_user)):
    a = store.q("SELECT * FROM alerts WHERE id=? AND customer_id=?", (aid, user["customer_id"] or -1))
    if not a:
        raise HTTPException(404, "Alert not found")
    status = "confirmed_by_customer" if body.action == "confirm" else "reported_fraud_card_frozen"
    store.x("UPDATE alerts SET status=? WHERE id=?", (status, aid))
    store.audit(user["email"], user["role"], "ALERT_RESPONSE", f"alert:{aid}", {"status": status})
    return {"ok": True, "status": status}


@app.post("/demo/suspicious-transaction")
async def demo_suspicious(user=Depends(S.current_user)):
    cid = customer_of(user)
    evt = await events.process(events.make_tx(events.profile(cid), True))
    return evt


# ------------------------------- market -------------------------------

def _forecasts() -> dict:
    return {r["symbol"]: r for r in db("SELECT * FROM forecasts")}


@app.get("/market/universe")
def universe():
    return {"symbols": hub.snapshot(), "status": market_status(), "forecasts": _forecasts()}


@app.get("/market/candles/{symbol}")
def candles(symbol: str, days: int = 180):
    rows = db("""SELECT strftime(date, '%Y-%m-%d') time, open, high, low, close, volume, source FROM prices_daily
                 WHERE symbol=? ORDER BY date DESC LIMIT ?""", [symbol, days])[::-1]
    if not rows:
        raise HTTPException(404, "Unknown symbol")
    return {"symbol": symbol, "daily": rows, "intraday": list(hub.candles.get(symbol, [])), "forecast": _forecasts().get(symbol)}


@app.get("/market/model-report")
def model_report():
    return {"forecast": json.loads((MODELS_DIR / "forecast_report.json").read_text()),
            "fraud": json.loads((MODELS_DIR / "fraud_report.json").read_text())}


@app.websocket("/ws/market")
async def ws_market(ws: WebSocket):
    await ws.accept()
    hub.clients.add(ws)
    await ws.send_text(json.dumps({"type": "ticks", "data": hub.snapshot(), "status": market_status()}))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.clients.discard(ws)


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    claims = S.decode(ws.cookies.get(COOKIE_NAME, ""))
    await ws.accept()
    if not claims:
        await ws.close(code=4401); return
    events.clients[ws] = {"role": claims["role"], "customer_id": claims.get("cid")}
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        events.clients.pop(ws, None)


# ------------------------------- invest -------------------------------

class RiskAnswers(BaseModel):
    horizon: int; experience: int; drawdown: int; goal: int; share: int


def _cust_features(cid: int) -> dict:
    o = db("SELECT age, sector, monthly_income FROM customers WHERE customer_id=?", [cid])[0]
    bal = db("SELECT SUM(balance) b FROM accounts WHERE customer_id=? AND currency='EGP'", [cid])[0]["b"] or 0
    inst = db("SELECT COALESCE(SUM(monthly_installment),0) i FROM loans WHERE customer_id=?", [cid])[0]["i"]
    return {**o, "savings_months": bal / max(o["monthly_income"], 1), "dti": inst / max(o["monthly_income"], 1)}


@app.post("/invest/risk-profile")
def set_risk(body: RiskAnswers, user=Depends(S.current_user)):
    cid = customer_of(user)
    band, notes = R.risk_band(body.model_dump(), _cust_features(cid))
    store.x("INSERT OR REPLACE INTO risk_profiles VALUES(?,?,?,?,?)", (user["id"], band, body.model_dump_json(), json.dumps(notes), store.now()))
    store.audit(user["email"], user["role"], "RISK_PROFILE", f"band:{band}")
    return {"band": band, "label": R.BANDS[band], "notes": notes}


@app.get("/invest/recommendations")
def recs(sharia: bool | None = None, user=Depends(S.current_user)):
    cid = customer_of(user)
    rp = store.q("SELECT band, notes FROM risk_profiles WHERE user_id=?", (user["id"],))
    if not rp:
        return {"needs_profile": True}
    band = rp[0]["band"]
    c = db("SELECT segment, sharia_preference FROM customers WHERE customer_id=?", [cid])[0]
    sh = c["sharia_preference"] if sharia is None else sharia
    held = {h["symbol"] for h in db("SELECT symbol FROM holdings WHERE customer_id=?", [cid])}
    pop = {r["symbol"]: r["n"] for r in db("""SELECT h.symbol, COUNT(*) n FROM holdings h JOIN customers c USING(customer_id)
                                              WHERE c.segment=? GROUP BY 1""", [c["segment"]])}
    picks = R.recommend(band, _forecasts(), held, bool(sh), pop)
    return {"band": band, "label": R.BANDS[band], "notes": json.loads(rp[0]["notes"]), "allocation": R.ALLOC[band], "sharia_only": bool(sh),
            "picks": picks, "holdings": db("SELECT * FROM holdings WHERE customer_id=?", [cid]),
            "disclaimer": "Educational recommendations generated by a model on demo data. Not investment advice. Forecasts are uncertain."}


# ------------------------------- assistant -------------------------------

class ChatIn(BaseModel):
    message: str


def _facts(intent: dict, cid: int, user) -> dict:
    i = intent["intent"]
    if i == "balance":
        acc = db("SELECT type,currency,balance FROM accounts WHERE customer_id=?", [cid])
        tot = sum(a["balance"] * (hub.price.get("USD/EGP", 48.6) if a["currency"] == "USD" else 1) for a in acc)
        return {"accounts": acc, "total_egp": round(tot, 2)}
    if i == "spending":
        if intent["period"] == "last_month":
            cond, lab_en, lab_ar = "date_trunc('month', ts) = date_trunc('month', ?::DATE - INTERVAL 1 MONTH)", "last month", "الشهر اللي فات"
        else:
            cond, lab_en, lab_ar = "ts >= ?::DATE - INTERVAL 30 DAY", "last 30 days", "آخر 30 يوم"
        cat = intent["category"]
        rows = db(f"SELECT category, SUM(amount) amount FROM transactions WHERE customer_id=? AND direction='debit' AND {cond} GROUP BY 1 ORDER BY 2 DESC", [cid, AS_OF])  # nosec B608 - cond is one of two fixed literals, values are bound
        total = sum(r["amount"] for r in rows if not cat or r["category"] == cat)
        return {"period_label": lab_en, "period_label_ar": lab_ar, "category": cat, "category_label": E.CATEGORIES[cat][0] if cat else None,
                "total": round(total, 2), "breakdown": [{"category": r["category"], "amount": round(r["amount"], 2)} for r in rows[:6]]}
    if i == "transactions":
        return {"recent": my_transactions(8, user)}
    if i in ("stock", "recommend"):
        f = _forecasts()
        if i == "stock" and intent["symbol"]:
            s = intent["symbol"]
            return {"symbol": s, "name": hub.meta.get(s, {}).get("name"), "live_price": round(hub.price.get(s, 0), 2),
                    "price_source": hub.source.get(s), "forecast": f.get(s), "model_note": "walk-forward accuracy is near 50% on this data; treat as low-confidence"}
        r = recs(None, user)
        if r.get("needs_profile"):
            return {"note": "Customer has not completed the risk questionnaire yet; ask them to open the Invest page."}
        return {"risk_band": r["label"][0], "allocation": r["allocation"], "top_picks": [{k: p[k] for k in ("symbol", "name", "prob_up", "vol_annual", "why")} for p in r["picks"][:4]]}
    if i == "security":
        return {"alerts": store.q("SELECT ts,title,risk_score,status FROM alerts WHERE customer_id=? ORDER BY id DESC LIMIT 5", (cid,))}
    if i == "fx":
        return {"USD/EGP": round(hub.price["USD/EGP"], 3), "gold_21k_egp_per_gram": round(hub.price["GOLD21"], 1), "source": "SIMULATED in demo"}
    return {"bank_products": ["Current & savings accounts (EGP/USD)", "Certificates of deposit 1/3/5 years (16-19.5%)", "Meeza & Visa debit cards",
                              "Credit cards", "Personal, auto and mortgage loans", "InstaPay transfers", "EGX & US stock investing with robo-advice"],
            "support": "Hotline 19xxx (demo)"}


@app.post("/chat")
async def chat_ep(body: ChatIn, user=Depends(S.current_user)):
    msg = body.message.strip()[:600]
    ar = bool(chat.AR.search(msg))
    if chat.INJECTION.search(msg):
        store.audit(user["email"], user["role"], "CHAT_BLOCKED", "", {"reason": "prompt-injection pattern"})
        txt = "عذراً، لا أستطيع تنفيذ هذا الطلب. أقدر أساعدك في حسابك أو استثماراتك." if ar else "Sorry, I can't do that. I can help with your own accounts and investments."
        return StreamingResponse(iter([txt]), media_type="text/plain; charset=utf-8")
    cid = customer_of(user)
    intent = chat.detect(msg, list(hub.meta))
    facts = _facts(intent, cid, user)
    store.audit(user["email"], user["role"], "CHAT", intent["intent"])

    async def gen():
        yield f"[[intent:{intent['intent']}]]"
        if intent["intent"] in ("balance", "spending"):
            # factual questions: exact deterministic answer (instant, no hallucination risk)
            f = dict(facts)
            if ar and f.get("period_label_ar"):
                f["period_label"] = f["period_label_ar"]
                if f.get("category"):
                    f["category_label"] = E.CATEGORIES[f["category"]][1]
            yield chat.template_answer(intent["intent"], f, ar)
            if f.get("breakdown"):
                yield ("\n\nأكبر بنود صرفك: " if ar else "\n\nTop categories: ") + " · ".join(
                    f"{(E.CATEGORIES[b['category']][1] if ar else E.CATEGORIES[b['category']][0]) if b['category'] in E.CATEGORIES else b['category']} {b['amount']:,.0f}" for b in f["breakdown"][:4])
            return
        got = False
        try:
            async for tok in chat.llama_stream(msg, facts):
                got = True
                yield tok
        except Exception as e:
            print("llm error", e)
        if not got:
            yield chat.template_answer(intent["intent"], facts, ar) + ("\n(المساعد الذكي غير متاح حالياً)" if ar else "\n(Llama offline - instant answer)")
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


# ------------------------------- staff console -------------------------------

@app.get("/staff/overview")
def staff_overview(user=Depends(S.require("advisor", "compliance", "admin"))):
    k = db("""SELECT (SELECT COUNT(*) FROM customers) customers, (SELECT COUNT(*) FROM accounts) accounts,
              (SELECT SUM(balance) FROM accounts WHERE currency='EGP') deposits_egp, (SELECT SUM(amount) FROM certificates) cds_egp,
              (SELECT COUNT(*) FROM transactions) transactions, (SELECT SUM(remaining) FROM loans) loans_egp,
              (SELECT AVG(CASE WHEN days_past_due>90 THEN 1.0 ELSE 0 END) FROM loans) npl_ratio,
              (SELECT COUNT(*) FROM customers WHERE is_investor) investors""")[0]
    return {"kpis": k,
            "by_governorate": db("SELECT governorate_en gov, governorate_ar gov_ar, COUNT(*) customers, AVG(monthly_income) avg_income FROM customers GROUP BY 1,2 ORDER BY 3 DESC"),
            "by_segment": db("SELECT segment, COUNT(*) n FROM customers GROUP BY 1 ORDER BY 2 DESC"),
            "monthly": db("""SELECT strftime("month", '%Y-%m') AS "month", direction, amount, n FROM agg_monthly"""),
            "open_alerts": store.q("SELECT COUNT(*) n FROM alerts WHERE status='open'")[0]["n"]}


@app.get("/staff/alerts")
def staff_alerts(user=Depends(S.require("compliance", "admin", "advisor"))):
    return {"alerts": store.q("SELECT * FROM alerts ORDER BY id DESC LIMIT 50"),
            "stats": store.q("SELECT kind, status, COUNT(*) n FROM alerts GROUP BY 1,2"),
            "live_flag_rate": store.q("SELECT AVG(flagged) r, COUNT(*) n FROM live_transactions")[0]}


@app.post("/staff/alerts/{aid}")
def staff_alert_status(aid: int, body: AlertAction, user=Depends(S.require("compliance", "admin"))):
    store.x("UPDATE alerts SET status=? WHERE id=?", ("closed_false_positive" if body.action == "dismiss" else "escalated_case", aid))
    store.audit(user["email"], user["role"], "ALERT_TRIAGE", f"alert:{aid}", {"action": body.action})
    return {"ok": True}


@app.get("/staff/customers")
def staff_search(q: str = "", user=Depends(S.require("advisor", "compliance", "admin"))):
    rows = db("""SELECT customer_id, cif, full_name_en, full_name_ar, governorate_en, segment, monthly_income, aml_risk FROM customers
                 WHERE full_name_en ILIKE ? OR cif ILIKE ? OR CAST(customer_id AS VARCHAR)=? LIMIT 20""", [f"%{q}%", f"%{q}%", q])
    return rows


@app.get("/staff/customers/{cid}")
def staff_customer(cid: int, user=Depends(S.require("advisor", "compliance", "admin"))):
    store.audit(user["email"], user["role"], "VIEW_CUSTOMER", f"customer:{cid}")
    # UEBA: bulk profile viewing by staff
    views = store.q("SELECT COUNT(*) n FROM audit_log WHERE actor=? AND action='VIEW_CUSTOMER' AND ts > ?",
                    (user["email"], (__import__("datetime").datetime.now(__import__("datetime").timezone.utc) - timedelta(hours=1)).isoformat()))[0]["n"]
    if views in (15, 30, 60):
        store.x("INSERT INTO alerts(ts,kind,customer_id,risk_score,title,reasons,payload) VALUES(?,?,?,?,?,?,?)",
                (store.now(), "insider", None, 70, f"Bulk profile viewing by {user['email']}", json.dumps([f"{views} customer profiles viewed in 1 hour"]), "{}"))
    p = _profile(cid)
    p["recent_transactions"] = db("SELECT ts,direction,amount,merchant,category,channel FROM transactions WHERE customer_id=? ORDER BY ts DESC LIMIT 10", [cid])
    p["views_last_hour"] = views
    return p


class Reveal(BaseModel):
    reason: str


@app.post("/staff/customers/{cid}/reveal")
def reveal(cid: int, body: Reveal, user=Depends(S.require("compliance"))):
    if len(body.reason.strip()) < 10:
        raise HTTPException(422, "A justification of at least 10 characters is required")
    store.audit(user["email"], user["role"], "BREAK_GLASS_PII", f"customer:{cid}", {"reason": body.reason})
    c = db("SELECT national_id, phone, email FROM customers WHERE customer_id=?", [cid])[0]
    return c


CATALOG = [
    ("customers", "national_id", "PII – Restricted", "masked by default; break-glass with reason"),
    ("customers", "full_name_ar / full_name_en", "PII", "visible to owner & assigned staff"),
    ("customers", "phone / email", "PII", "masked for staff"),
    ("customers", "birth_date / gender", "PII", "aggregated (age bands) in BI"),
    ("customers", "monthly_income / credit_score", "Sensitive – Financial", "role-based access"),
    ("accounts", "iban / balance", "Sensitive – Financial", "IBAN masked except owner"),
    ("cards", "last4 / expiry", "PCI – limited", "full PAN never stored"),
    ("transactions", "amount / merchant / governorate", "Sensitive – Financial", "owner + compliance"),
    ("login_events", "ip / user_agent", "Security telemetry", "retained 12 months"),
    ("audit_log", "*", "Security – Immutable", "hash-chained, append-only"),
    ("prices_daily / forecasts", "*", "Public / Internal", "no personal data"),
]


@app.get("/staff/governance")
def governance(user=Depends(S.require("compliance", "admin", "advisor"))):
    return {"catalog": [dict(zip(["table", "columns", "classification", "control"], c)) for c in CATALOG],
            "dq": db("SELECT * FROM dq_results"),
            "audit_chain": store.verify_audit_chain(),
            "audit_recent": store.q("SELECT id,ts,actor,role,action,target,substr(hash,1,12) hash FROM audit_log ORDER BY id DESC LIMIT 25"),
            "consents": store.q("SELECT COUNT(*) users, SUM(ai_assistant) ai, SUM(marketing) marketing FROM consents")[0],
            "retention": [{"data": "Transactions", "policy": "10 years (banking record keeping)"}, {"data": "Login telemetry", "policy": "12 months"},
                          {"data": "Chat transcripts", "policy": "90 days, then deleted"}, {"data": "Marketing consent", "policy": "until withdrawn"}],
            "regulation": ["Egypt PDPL Law 151/2020 + Executive Regulations (Decree 816/2025)", "CBE data & cyber-security rules (Banking Law 194/2020)",
                           "FRA Decree 57/2024 (robo-advisory suitability)", "Data stays in Egypt; LLM runs locally (no data leaves the server)"]}


@app.get("/staff/models")
def staff_models(user=Depends(S.require("compliance", "admin", "advisor"))):
    return model_report()

"""Live streams: market ticks (Finnhub WebSocket or labelled simulation) and bank transactions with real-time fraud scoring.
In production these become Kafka topics (market.ticks, bank.transactions, alerts.fraud)."""
from __future__ import annotations

import asyncio
import json
import random
from collections import deque
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import duckdb
import numpy as np

from . import egypt as E, store
from .config import DUCKDB_PATH, FINNHUB_API_KEY

CAIRO = ZoneInfo("Africa/Cairo"); NY = ZoneInfo("America/New_York")


def market_status() -> dict:
    c = datetime.now(CAIRO); n = datetime.now(NY)
    egx_open = c.weekday() in (6, 0, 1, 2, 3) and (10, 0) <= (c.hour, c.minute) < (14, 30)
    us_open = n.weekday() < 5 and (9, 30) <= (n.hour, n.minute) < (16, 0)
    return {"cairo_time": c.strftime("%a %H:%M"), "EGX": {"open": egx_open, "hours": "Sun–Thu 10:00–14:30 Cairo"},
            "US": {"open": us_open, "hours": "Mon–Fri 09:30–16:00 New York"}}


class MarketHub:
    def __init__(self):
        self.meta = {u[0]: {"symbol": u[0], "name": u[1], "name_ar": u[2], "market": u[3], "sector": u[4], "sharia": u[7], "vol": u[6]} for u in E.UNIVERSE}
        self.meta["USD/EGP"] = {"symbol": "USD/EGP", "name": "US Dollar / Egyptian Pound", "name_ar": "الدولار / الجنيه", "market": "FX", "sector": "FX", "sharia": True, "vol": 0.08}
        self.meta["GOLD21"] = {"symbol": "GOLD21", "name": "Gold 21K (EGP / gram)", "name_ar": "ذهب عيار 21 (جنيه/جرام)", "market": "FX", "sector": "Gold", "sharia": True, "vol": 0.15}
        self.price, self.prev_close, self.source, self.last_live = {}, {}, {}, {}
        self.candles = {s: deque(maxlen=240) for s in self.meta}
        self.clients: set = set()
        self.loaded = False

    def load(self):
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        rows = con.execute("""SELECT symbol, close, source, LAG(close) OVER (PARTITION BY symbol ORDER BY date) prev
                              FROM prices_daily QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC)=1""").fetchall()
        con.close()
        for s, c, src, prev in rows:
            self.price[s] = c; self.prev_close[s] = prev or c; self.source[s] = "SIMULATED"
        for s, p in (("USD/EGP", 48.6), ("GOLD21", 4000 * 48.6 / 31.1035 * 0.875)):
            self.price[s] = p; self.prev_close[s] = p; self.source[s] = "SIMULATED"
        self.loaded = True

    def tick(self, s: str, p: float, src: str):
        self.price[s] = p; self.source[s] = src
        minute = int(datetime.now(timezone.utc).timestamp() // 60 * 60)
        dq = self.candles[s]
        if dq and dq[-1]["time"] == minute:
            c = dq[-1]; c["high"] = max(c["high"], p); c["low"] = min(c["low"], p); c["close"] = p
        else:
            dq.append({"time": minute, "open": p, "high": p, "low": p, "close": p})

    def snapshot(self) -> list[dict]:
        out = []
        for s, m in self.meta.items():
            if s not in self.price:
                continue
            p = self.price[s]; pc = self.prev_close[s]
            out.append({**m, "price": round(p, 4), "change_pct": round((p / pc - 1) * 100, 2), "source": self.source[s]})
        return out

    async def broadcast(self, msg: dict):
        dead = []
        data = json.dumps(msg)
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def simulate_loop(self):
        rng = np.random.default_rng()
        while True:
            now = asyncio.get_event_loop().time()
            for s, m in self.meta.items():
                if s not in self.price:
                    continue
                if now - self.last_live.get(s, -1e9) < 60:
                    continue                    # real Finnhub trades are flowing for this symbol
                sig = m["vol"] / np.sqrt(252 * 6.5 * 3600) * 6
                drift_back = 0.002 * (np.log(self.prev_close[s]) - np.log(self.price[s]))
                self.tick(s, self.price[s] * float(np.exp(drift_back + sig * rng.standard_normal())), "SIMULATED")
            await self.broadcast({"type": "ticks", "data": self.snapshot(), "status": market_status()})
            await asyncio.sleep(1.0)

    async def finnhub_loop(self):
        if not FINNHUB_API_KEY:
            return
        import websockets
        us = [u[0] for u in E.US]
        while True:
            try:
                async with websockets.connect(f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}") as ws:
                    for s in us:
                        await ws.send(json.dumps({"type": "subscribe", "symbol": s}))
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("type") == "trade":
                            for t in msg["data"]:
                                self.last_live[t["s"]] = asyncio.get_event_loop().time()
                                self.tick(t["s"], float(t["p"]), "LIVE · Finnhub")
            except Exception as e:
                print("finnhub ws error:", e)
                await asyncio.sleep(10)


hub = MarketHub()


# ----------------------- live transactions + fraud -----------------------

class EventHub:
    def __init__(self):
        self.clients: dict = {}   # ws -> user dict
        self.sample: list[dict] = []
        self.scorer = None

    def load(self):
        from .ml_fraud import Scorer
        self.scorer = Scorer()
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        demo = con.execute("SELECT demo_customer_id FROM demo_meta").fetchone()[0]
        rows = con.execute("""SELECT c.customer_id, c.monthly_income income, c.governorate_en home_gov, AVG(t.amount) cust_avg
            FROM customers c JOIN transactions t USING(customer_id) WHERE t.direction='debit' AND NOT t.is_fraud
            AND (c.customer_id % 37 = 0 OR c.customer_id=?) GROUP BY 1,2,3 LIMIT 3000""", [demo]).fetchall()
        con.close()
        self.sample = [dict(zip(["customer_id", "income", "home_gov", "cust_avg"], r)) for r in rows]
        self.by_id = {r["customer_id"]: r for r in self.sample}

    def profile(self, cid: int) -> dict:
        if cid in self.by_id:
            return self.by_id[cid]
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        r = con.execute("""SELECT c.customer_id, c.monthly_income, c.governorate_en, AVG(t.amount) FROM customers c JOIN transactions t USING(customer_id)
                           WHERE c.customer_id=? AND t.direction='debit' GROUP BY 1,2,3""", [cid]).fetchone()
        con.close()
        p = dict(zip(["customer_id", "income", "home_gov", "cust_avg"], r)); self.by_id[cid] = p
        return p

    def make_tx(self, prof: dict, suspicious: bool) -> dict:
        cats = list(E.CATEGORIES)
        if suspicious:
            kind = random.choice(["takeover", "cnp", "atm"])
            cat = {"takeover": "transfers", "cnp": "shopping", "atm": "cash"}[kind]
            merchant = {"takeover": "InstaPay transfer", "cnp": "Online merchant (overseas)", "atm": "ATM withdrawal"}[kind]
            channel = {"takeover": "InstaPay", "cnp": "E-commerce", "atm": "ATM"}[kind]
            amount = round(prof["cust_avg"] * random.uniform(8, 25), 2)
            gov = random.choice([g[1] for g in E.GOVERNORATES if g[1] != prof["home_gov"]])
            hour = random.randint(0, 4); new_dev = True; vel = random.randint(3, 8)
        else:
            cat = random.choices(cats, weights=[E.CATEGORY_WEIGHTS[c] for c in cats])[0]
            merchant = random.choice(E.CATEGORIES[cat][2]); channel = random.choice(E.CATEGORIES[cat][3])
            amount = round(prof["cust_avg"] * random.lognormvariate(-0.3, 0.6), 2)
            gov = prof["home_gov"]; hour = datetime.now(CAIRO).hour; new_dev = False; vel = 1
        return {"customer_id": prof["customer_id"], "amount": amount, "category": cat, "merchant": merchant, "channel": channel,
                "governorate": gov, "home_gov": prof["home_gov"], "hour": hour, "new_device": new_dev, "velocity_1h": vel,
                "cust_avg": prof["cust_avg"], "income": prof["income"]}

    async def process(self, tx: dict) -> dict:
        score, reasons = self.scorer.score(tx)
        flagged = score >= 60
        store.x("INSERT INTO live_transactions(ts,customer_id,amount,merchant,category,channel,governorate,risk_score,flagged) VALUES(?,?,?,?,?,?,?,?,?)",
                (store.now(), tx["customer_id"], tx["amount"], tx["merchant"], tx["category"], tx["channel"], tx["governorate"], score, int(flagged)))
        evt = {"type": "transaction", "tx": {k: tx[k] for k in ("customer_id", "amount", "merchant", "category", "channel", "governorate")},
               "risk_score": score, "flagged": flagged, "reasons": reasons, "ts": store.now()}
        if flagged:
            aid = store.x("INSERT INTO alerts(ts,kind,customer_id,risk_score,title,reasons,payload) VALUES(?,?,?,?,?,?,?)",
                          (store.now(), "fraud", tx["customer_id"], score, f"Suspicious {tx['channel']} of EGP {tx['amount']:,.0f} at {tx['merchant']}",
                           json.dumps(reasons), json.dumps(evt["tx"])))
            evt["alert_id"] = aid
        await self.broadcast(evt)
        return evt

    async def broadcast(self, evt: dict):
        data = json.dumps(evt, default=str)
        for ws, user in list(self.clients.items()):
            staff = user["role"] in ("compliance", "admin", "advisor")
            mine = user.get("customer_id") == evt["tx"]["customer_id"]
            if not (staff or mine):
                continue
            if staff and not evt["flagged"] and not mine and random.random() < 0.5:
                continue        # thin out normal traffic for staff
            try:
                await ws.send_text(data)
            except Exception:
                self.clients.pop(ws, None)

    async def loop(self):
        while True:
            prof = random.choice(self.sample)
            await self.process(self.make_tx(prof, random.random() < 0.06))
            await asyncio.sleep(random.uniform(1.0, 2.5))


events = EventHub()

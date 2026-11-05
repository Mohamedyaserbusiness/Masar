"""Daily price history: Twelve Data (official API, free key) for US/FX/gold, labelled simulation otherwise."""
from __future__ import annotations

import time
from datetime import timedelta

import httpx
import numpy as np
import pandas as pd

from . import egypt as E
from .config import AS_OF, TWELVEDATA_API_KEY

DAYS = 1500


def _trading_days(market: str) -> pd.DatetimeIndex:
    days = pd.date_range(end=pd.Timestamp(AS_OF) - timedelta(days=1), periods=int(DAYS * 1.45), freq="D")
    wd = days.weekday
    keep = (wd <= 3) | (wd == 6) if market == "EGX" else (wd <= 4)   # EGX trades Sun-Thu
    return days[keep][-DAYS:]


def simulate(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = []
    mkt_f = {m: rng.standard_normal(DAYS) for m in ("EGX", "US")}
    sectors = {u[4] for u in E.UNIVERSE}
    sec_f = {s: rng.standard_normal(DAYS) for s in sectors}
    for sym, name, _, market, sector, base, vol, _ in E.UNIVERSE:
        idx = _trading_days(market)
        dv = vol / np.sqrt(252)
        drift = (0.22 if market == "EGX" else 0.10) / 252
        eps = 0.55 * mkt_f[market] + 0.35 * sec_f[sector] + 0.76 * rng.standard_normal(DAYS)
        # mild volatility clustering
        sv = dv * np.exp(0.3 * np.convolve(rng.standard_normal(DAYS), np.ones(20) / 20, mode="same"))
        r = drift - 0.5 * sv ** 2 + sv * eps
        close = base * np.exp(np.cumsum(r) - np.sum(r))     # ends near base price
        op = close * np.exp(rng.normal(0, dv / 3, DAYS))
        hi = np.maximum(op, close) * np.exp(np.abs(rng.normal(0, dv / 2, DAYS)))
        lo = np.minimum(op, close) * np.exp(-np.abs(rng.normal(0, dv / 2, DAYS)))
        volm = (rng.lognormal(13 if market == "EGX" else 16, 0.4, DAYS)).astype(int)
        out.append(pd.DataFrame({"symbol": sym, "date": idx, "open": op, "high": hi, "low": lo, "close": close, "volume": volm, "source": "SIMULATED"}))
    return pd.concat(out, ignore_index=True)


def _twelvedata(symbol: str) -> pd.DataFrame | None:
    try:
        r = httpx.get("https://api.twelvedata.com/time_series", params={"symbol": symbol, "interval": "1day", "outputsize": DAYS, "apikey": TWELVEDATA_API_KEY}, timeout=30)
        js = r.json()
        if js.get("status") != "ok":
            print("  twelvedata", symbol, js.get("message", "")[:80]); return None
        df = pd.DataFrame(js["values"])
        df["date"] = pd.to_datetime(df["datetime"])
        for c in ("open", "high", "low", "close"):
            df[c] = df[c].astype(float)
        df["volume"] = df.get("volume", pd.Series(0, index=df.index)).astype(float).astype(int)
        return df[["date", "open", "high", "low", "close", "volume"]].sort_values("date")
    except Exception as e:  # network etc.
        print("  twelvedata error", symbol, e); return None


def build_history() -> pd.DataFrame:
    hist = simulate()
    if not TWELVEDATA_API_KEY:
        print("  no TWELVEDATA_API_KEY -> all prices SIMULATED")
        return hist
    real = []
    for i, (sym, *_rest) in enumerate(E.US):
        if i and i % 7 == 0:
            time.sleep(61)          # free plan: 8 requests/minute
        df = _twelvedata(sym)
        if df is not None:
            df["symbol"] = sym; df["source"] = "TWELVE DATA"
            real.append(df)
    if real:
        got = {d.symbol.iat[0] for d in real}
        hist = pd.concat([hist[~hist.symbol.isin(got)], *real], ignore_index=True)
        print("  real US history for", sorted(got))
    return hist

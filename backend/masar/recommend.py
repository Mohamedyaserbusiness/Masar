"""Suitability-first stock recommendations (FRA Decree 57/2024 spirit: risk tolerance, objectives, solvency)."""
from __future__ import annotations

from . import egypt as E

BANDS = {1: ("Conservative", "متحفظ"), 2: ("Moderately conservative", "متحفظ نسبياً"), 3: ("Balanced", "متوازن"),
         4: ("Growth", "نمو"), 5: ("Aggressive", "مغامر")}
VOL_CAP = {1: 0.30, 2: 0.34, 3: 0.40, 4: 0.50, 5: 0.80}
ALLOC = {1: {"Bank certificates (CDs)": 55, "Money-market fund": 20, "Gold": 15, "EGX stocks": 10, "US stocks": 0},
         2: {"Bank certificates (CDs)": 40, "Money-market fund": 15, "Gold": 20, "EGX stocks": 20, "US stocks": 5},
         3: {"Bank certificates (CDs)": 25, "Money-market fund": 10, "Gold": 15, "EGX stocks": 38, "US stocks": 12},
         4: {"Bank certificates (CDs)": 10, "Money-market fund": 5, "Gold": 10, "EGX stocks": 50, "US stocks": 25},
         5: {"Bank certificates (CDs)": 5, "Money-market fund": 0, "Gold": 5, "EGX stocks": 55, "US stocks": 35}}


def risk_band(answers: dict, customer: dict) -> tuple[int, list[str]]:
    """answers: horizon, experience, drawdown, goal, share  (each 1..5)"""
    q = sum(int(answers.get(k, 3)) for k in ("horizon", "experience", "drawdown", "goal", "share")) / 5
    notes = []
    adj = 0.0
    if customer.get("age", 40) >= 60: adj -= 0.5; notes.append("age 60+ lowers capacity for risk")
    if customer.get("sector") in ("Government", "Pension"): adj += 0.2; notes.append("stable income")
    if customer.get("sector") in ("Self-employed", "Student"): adj -= 0.3; notes.append("variable income")
    if customer.get("savings_months", 0) < 3: adj -= 0.5; notes.append("emergency fund below 3 months")
    if customer.get("dti", 0) > 0.4: adj -= 0.5; notes.append("high debt-to-income")
    band = int(min(5, max(1, round(q + adj))))
    return band, notes


def recommend(band: int, forecasts: dict, holdings: set[str], sharia_only: bool, popular: dict[str, int], us_allowed: bool = True) -> list[dict]:
    cands = []
    for sym, name, name_ar, market, sector, _, _, sharia in E.UNIVERSE:
        f = forecasts.get(sym)
        if not f:
            continue
        if sharia_only and not sharia:
            continue
        if market == "US" and (not us_allowed or ALLOC[band]["US stocks"] == 0):
            continue
        vol = f["vol_annual"]
        if vol > VOL_CAP[band]:
            continue          # hard suitability constraint
        fscore = (f["prob_up"] - 0.5) * 4 + f["exp_ret_5d"] * 20
        mom = f.get("mom_3m") or 0
        stab = 1 - vol / VOL_CAP[band]
        div = 0.5 if sym not in holdings else -0.5
        pop = min(1.0, popular.get(sym, 0) / (max(popular.values()) + 1)) if popular else 0
        score = 0.35 * fscore + 0.2 * mom + (0.3 if band <= 2 else 0.15) * stab + 0.15 * div + 0.15 * pop
        why = [f"Volatility {vol:.0%} fits your '{BANDS[band][0]}' profile (cap {VOL_CAP[band]:.0%})"]
        if f["prob_up"] > 0.52: why.append(f"Model: {f['prob_up']:.0%} chance of an up day ({f['confidence']} confidence)")
        if mom > 0.05: why.append(f"Positive 3-month momentum (+{mom:.0%})")
        if sym not in holdings: why.append("Adds diversification to your portfolio")
        if pop > 0.4: why.append("Popular with customers like you")
        if sharia: why.append("Sharia-compliant")
        cands.append({"symbol": sym, "name": name, "name_ar": name_ar, "market": market, "sector": sector, "score": round(score, 4),
                      "sharia": sharia, "vol_annual": vol, "prob_up": f["prob_up"], "exp_ret_5d": f["exp_ret_5d"],
                      "last_close": f["last_close"], "confidence": f["confidence"], "why": why})
    cands.sort(key=lambda c: -c["score"])
    picks, per_sector = [], {}
    for c in cands:                       # diversification: max 2 per sector
        if per_sector.get(c["sector"], 0) >= 2:
            continue
        picks.append(c); per_sector[c["sector"]] = per_sector.get(c["sector"], 0) + 1
        if len(picks) == 6:
            break
    return picks

"""Synthetic Egyptian bank data: 100k customers + accounts, cards, loans, CDs, transactions, logins, holdings."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from . import egypt as E
from .config import AS_OF


def _in(d: np.ndarray, rng_: tuple[date, date]) -> np.ndarray:
    a = np.datetime64(rng_[0]); b = np.datetime64(rng_[1])
    return (d >= a) & (d <= b)


def generate(n: int = 100_000, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    cid = np.arange(1, n + 1)

    # ---------- customers ----------
    gw = np.array([g[3] for g in E.GOVERNORATES]); gw = gw / gw.sum()
    gi = rng.choice(len(E.GOVERNORATES), n, p=gw)
    male = rng.random(n) < 0.57
    age = (18 + rng.beta(2.0, 3.2, n) * 62).astype(int)
    birth = [AS_OF - timedelta(days=int(a * 365.25 + r)) for a, r in zip(age, rng.integers(0, 365, n))]

    ow = np.array([o[6] for o in E.OCCUPATIONS], float); ow /= ow.sum()
    occ = rng.choice(len(E.OCCUPATIONS), n, p=ow)
    student_i = [i for i, o in enumerate(E.OCCUPATIONS) if o[2] == "Student"][0]
    retired_i = [i for i, o in enumerate(E.OCCUPATIONS) if o[2] == "Pension"][0]
    occ = np.where((age < 23) & (rng.random(n) < 0.6), student_i, occ)
    occ = np.where((age >= 60) & (rng.random(n) < 0.7), retired_i, occ)
    occ = np.where((occ == student_i) & (age > 27), 2, occ)
    occ = np.where((occ == retired_i) & (age < 50), 2, occ)

    med = np.array([o[3] for o in E.OCCUPATIONS])[occ]
    sig = np.array([o[4] for o in E.OCCUPATIONS])[occ]
    flo = np.array([o[5] for o in E.OCCUPATIONS])[occ]
    region = np.array([g[4] for g in E.GOVERNORATES])[gi]
    gmult = np.select([region == "Greater Cairo", region == "Alexandria & Matrouh", region == "Upper Egypt", region == "Frontier"],
                      [1.15, 1.05, 0.85, 1.05], 0.92)
    income = np.maximum(med * gmult * np.exp(sig * rng.standard_normal(n)), flo)
    income = (np.round(income / 50) * 50).astype(int)
    seg_i = np.digitize(income, [15000, 40000, 100000])
    seg_names = np.array(["Mass", "Mass Affluent", "Affluent", "Private"])

    mi = rng.integers(0, len(E.MALE), n); fi = rng.integers(0, len(E.FEMALE), n)
    pi = rng.integers(0, len(E.MALE), n); li = rng.integers(0, len(E.FAMILY), n)
    first_ar = np.where(male, np.array([m[0] for m in E.MALE])[mi], np.array([f[0] for f in E.FEMALE])[fi])
    first_en = np.where(male, np.array([m[1] for m in E.MALE])[mi], np.array([f[1] for f in E.FEMALE])[fi])
    father_ar = np.array([m[0] for m in E.MALE])[pi]; father_en = np.array([m[1] for m in E.MALE])[pi]
    fam_ar = np.array([f[0] for f in E.FAMILY])[li]; fam_en = np.array([f[1] for f in E.FAMILY])[li]
    domains = np.array(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"])[rng.choice(4, n, p=[.62, .16, .12, .10])]
    emails = [f"{a.lower()}.{b.lower().replace('-', '')}{c}@{d}" for a, b, c, d in zip(first_en, fam_en, cid, domains)]
    pref = np.array(["010", "011", "012", "015"])[rng.choice(4, n, p=[.4, .2, .25, .15])]
    phones = [f"+20{p[1:]}{(c * 48271) % 100_000_000:08d}" for p, c in zip(pref, cid)]
    gov_codes = np.array([g[0] for g in E.GOVERNORATES])[gi]
    nids = [E.make_national_id(b, g, bool(m), int(c)) for b, g, m, c in zip(birth, gov_codes, male, cid)]
    cities = [E.GOVERNORATES[g][5][r % len(E.GOVERNORATES[g][5])] for g, r in zip(gi, rng.integers(0, 100, n))]

    p_dig = np.select([age < 35, age < 50, age < 65], [0.85, 0.7, 0.45], 0.25) + 0.1 * (seg_i >= 2)
    digital = rng.random(n) < p_dig
    p_inv = np.array([0.06, 0.18, 0.35, 0.6])[seg_i] * np.where((age >= 25) & (age <= 60), 1.2, 0.7)
    investor = rng.random(n) < p_inv
    married = rng.random(n) < np.clip((age - 22) / 15, 0, 0.8)
    dependents = np.where(married, rng.poisson(2.0, n), 0)
    since_years = np.minimum(rng.exponential(5, n), age - 18)
    since = [AS_OF - timedelta(days=int(y * 365)) for y in since_years]
    credit = np.clip(600 + 40 * np.log(income / 9000) + 1.5 * (age - 35) + rng.normal(0, 55, n), 400, 850).astype(int)

    customers = pd.DataFrame({
        "customer_id": cid, "cif": [f"MSR{c:08d}" for c in cid],
        "full_name_en": [f"{a} {b} {c}" for a, b, c in zip(first_en, father_en, fam_en)],
        "full_name_ar": [f"{a} {b} {c}" for a, b, c in zip(first_ar, father_ar, fam_ar)],
        "first_name_en": first_en, "first_name_ar": first_ar,
        "gender": np.where(male, "M", "F"), "birth_date": pd.to_datetime(birth), "age": age,
        "national_id": nids, "phone": phones, "email": emails,
        "governorate_code": gov_codes, "governorate_en": np.array([g[1] for g in E.GOVERNORATES])[gi],
        "governorate_ar": np.array([g[2] for g in E.GOVERNORATES])[gi], "region": region, "city": cities,
        "occupation_en": np.array([o[0] for o in E.OCCUPATIONS])[occ], "occupation_ar": np.array([o[1] for o in E.OCCUPATIONS])[occ],
        "sector": np.array([o[2] for o in E.OCCUPATIONS])[occ], "monthly_income": income,
        "segment": seg_names[seg_i], "marital_status": np.where(married, "Married", "Single"), "dependents": dependents,
        "customer_since": pd.to_datetime(since),
        "kyc_status": rng.choice(["Verified", "Pending review", "Expired documents"], n, p=[.95, .04, .01]),
        "aml_risk": rng.choice(["Low", "Medium", "High"], n, p=[.86, .12, .02]),
        "digital_active": digital, "is_investor": investor, "sharia_preference": rng.random(n) < 0.35,
        "preferred_language": np.where(rng.random(n) < 0.7, "ar", "en"), "credit_score": credit,
    })

    # ---------- accounts ----------
    has_sav = rng.random(n) < np.clip(0.45 + 0.004 * age + 0.1 * seg_i, 0, 0.95)
    has_usd = (rng.random(n) < 0.04 + 0.05 * seg_i) | ((customers.sector == "Remittance").to_numpy() & (rng.random(n) < 0.4))
    rows = []
    for kind, mask, mult, cur in [("Current", np.ones(n, bool), 1, "EGP"), ("Savings", has_sav, 2, "EGP"), ("USD Savings", has_usd, 3, "USD")]:
        ids = cid[mask]; inc = income[mask]
        if kind == "Current":
            bal = inc * rng.lognormal(np.log(1.1), 0.8, len(ids))
        elif kind == "Savings":
            bal = inc * rng.lognormal(np.log(4), 1.0, len(ids))
        else:
            bal = inc / 48 * rng.lognormal(np.log(3), 1.0, len(ids))
        rows.append(pd.DataFrame({"account_id": ids * 10 + mult, "customer_id": ids, "type": kind, "currency": cur,
                                  "balance": np.round(bal, 2), "interest_rate": {"Current": 0.0, "Savings": 15.5, "USD Savings": 1.5}[kind]}))
    accounts = pd.concat(rows, ignore_index=True)
    branch = 100 + (accounts.customer_id.to_numpy() % 270)
    accounts["iban"] = [E.make_iban(int(b), int(a)) for b, a in zip(branch, accounts.account_id)]
    accounts["status"] = "Active"

    # ---------- cards ----------
    deb = rng.random(n) < 0.92
    cre = rng.random(n) < np.array([0.12, 0.3, 0.55, 0.8])[seg_i]
    cards = pd.concat([
        pd.DataFrame({"customer_id": cid[deb], "card_type": rng.choice(["Meeza Debit", "Visa Debit"], deb.sum(), p=[.4, .6]),
                      "credit_limit": 0.0, "outstanding": 0.0}),
        pd.DataFrame({"customer_id": cid[cre], "card_type": rng.choice(["Visa Classic Credit", "Mastercard Titanium", "Visa Platinum"], cre.sum(), p=[.5, .3, .2]),
                      "credit_limit": np.round(income[cre] * rng.uniform(2, 5, cre.sum()), -2),
                      "outstanding": 0.0}),
    ], ignore_index=True)
    cards["outstanding"] = np.where(cards.credit_limit > 0, np.round(cards.credit_limit * rng.beta(1.5, 4, len(cards)), 2), 0)
    cards["last4"] = rng.integers(1000, 9999, len(cards)).astype(str)
    cards["expiry"] = [f"{m:02d}/{y}" for m, y in zip(rng.integers(1, 13, len(cards)), rng.integers(27, 31, len(cards)))]
    cards["status"] = "Active"

    # ---------- loans & certificates ----------
    lt = rng.random(n)
    lkind = np.select([lt < 0.18, lt < 0.22, lt < 0.24], ["Personal loan", "Auto loan", "Mortgage"], "")
    lm = lkind != ""
    prin = income[lm] * np.select([lkind[lm] == "Personal loan", lkind[lm] == "Auto loan"], [rng.uniform(8, 30, lm.sum()), rng.uniform(20, 60, lm.sum())], rng.uniform(60, 150, lm.sum()))
    tenor = np.select([lkind[lm] == "Personal loan", lkind[lm] == "Auto loan"], [60, 60], 180)
    rate = rng.uniform(24, 30, lm.sum())
    r = rate / 1200
    inst = prin * r / (1 - (1 + r) ** -tenor)
    dpd = rng.choice([0, 15, 45, 75, 120], lm.sum(), p=[.88, .06, .03, .015, .015])
    loans = pd.DataFrame({"customer_id": cid[lm], "loan_type": lkind[lm], "principal": np.round(prin, -2), "rate": np.round(rate, 2),
                          "tenor_months": tenor, "monthly_installment": np.round(inst, 2), "remaining": np.round(prin * rng.uniform(0.2, 0.95, lm.sum()), -2),
                          "days_past_due": dpd})
    cdm = rng.random(n) < np.clip(0.1 + 0.004 * age + 0.06 * seg_i, 0, 0.8)
    certificates = pd.DataFrame({"customer_id": cid[cdm], "amount": np.round(income[cdm] * rng.lognormal(np.log(8), 0.8, cdm.sum()), -3),
                                 "rate": np.round(rng.choice([16.0, 17.25, 18.0, 19.5], cdm.sum()), 2),
                                 "term_years": rng.choice([1, 3, 5], cdm.sum(), p=[.5, .35, .15]),
                                 "start_date": pd.to_datetime([AS_OF - timedelta(days=int(d)) for d in rng.integers(30, 1000, cdm.sum())])})
    certificates["maturity_date"] = certificates.start_date + pd.to_timedelta(certificates.term_years * 365, unit="D")

    # credit score penalty for arrears
    pen = pd.Series(dpd, index=cid[lm] - 1)
    cs = customers.credit_score.to_numpy().copy()
    cs[pen.index.to_numpy()] = np.clip(cs[pen.index.to_numpy()] - pen.to_numpy(), 400, 850)
    customers["credit_score"] = cs

    transactions = _transactions(rng, customers, income, seg_i, gi)
    logins = _logins(rng, customers)
    holdings = _holdings(rng, customers, income)
    return {"customers": customers, "accounts": accounts, "cards": cards, "loans": loans,
            "certificates": certificates, "transactions": transactions, "login_events": logins, "holdings": holdings}


def _transactions(rng, customers, income, seg_i, gi) -> pd.DataFrame:
    n = len(customers)
    start = np.datetime64(AS_OF - timedelta(days=365), "s")
    lam = np.array([2.2, 4.5, 7.0, 10.0])[seg_i] * np.where(customers.digital_active, 1.4, 0.8) * rng.lognormal(0, 0.5, n)
    cnt = rng.poisson(lam * 12)
    ci = np.repeat(np.arange(n), cnt)
    T = len(ci)
    cats = list(E.CATEGORIES)
    base = np.array([E.CATEGORY_WEIGHTS[c] for c in cats], float)
    cat = np.empty(T, dtype=np.int16)
    rs = seg_i[ci]
    for s in range(4):
        w = base.copy()
        w[cats.index("cash")] *= [1.5, 1.1, 0.8, 0.6][s]
        w[cats.index("travel")] *= [0.5, 1, 2.5, 4][s]
        w[cats.index("dining")] *= [0.8, 1, 1.3, 1.5][s]
        w[cats.index("shopping")] *= [0.8, 1, 1.3, 1.6][s]
        m = rs == s
        cat[m] = rng.choice(len(cats), m.sum(), p=w / w.sum())
    hw = np.array([2, 1, .6, .4, .3, .4, .8, 1.5, 2.5, 3.5, 4.5, 5, 5.5, 6, 6, 5.5, 5.5, 6, 6.5, 7, 7.5, 7, 5.5, 3.5]); hw /= hw.sum()
    secs = rng.integers(0, 365, T) * 86400 + rng.choice(24, T, p=hw) * 3600 + rng.integers(0, 3600, T)
    ts = start + secs.astype("timedelta64[s]")
    day = ts.astype("datetime64[D]")

    share = np.array([E.CATEGORIES[c][4] for c in cats])[cat]
    amt = income[ci] * share * rng.lognormal(0, 0.55, T)
    mult = np.ones(T)
    def bump(window, cname, f):
        mult[_in(day, window) & (cat == cats.index(cname))] *= f
    for c, f in [("groceries", 1.5), ("dining", 1.3), ("charity", 3.0)]:
        bump(E.RAMADAN_2026, c, f)
    for w in (E.EID_FITR_2026, E.EID_ADHA_2026):
        bump(w, "shopping", 1.8); bump(w, "cash", 1.6)
    bump(E.SUMMER, "travel", 2.5)
    bump(E.BACK_TO_SCHOOL, "education", 2.0); bump(E.BACK_TO_SCHOOL, "shopping", 1.3)
    infl = 1 + 0.13 * (secs / (365 * 86400)) - 0.065
    amt = amt * mult * infl
    is_cash = cat == cats.index("cash")
    amt = np.where(is_cash, np.clip(np.round(amt / 100) * 100, 200, 30000), np.clip(amt, 10, None))
    amt = np.round(amt, 2)

    merch = np.empty(T, dtype=object); chan = np.empty(T, dtype=object)
    for k, c in enumerate(cats):
        m = cat == k
        ms = E.CATEGORIES[c][2]; ch = E.CATEGORIES[c][3]
        merch[m] = np.array(ms, dtype=object)[rng.integers(0, len(ms), m.sum())]
        chan[m] = np.array(ch, dtype=object)[rng.integers(0, len(ch), m.sum())]
    gov_en = np.array([g[1] for g in E.GOVERNORATES], dtype=object)
    home = gi[ci]
    away = (rng.random(T) < 0.04) | ((cat == cats.index("travel")) & (rng.random(T) < 0.6))
    tgov = np.where(away, rng.integers(0, len(E.GOVERNORATES), T), home)

    deb = pd.DataFrame({"customer_id": customers.customer_id.to_numpy()[ci], "ts": ts, "direction": "debit",
                        "amount": amt, "category": np.array(cats, dtype=object)[cat], "merchant": merch, "channel": chan,
                        "governorate": gov_en[tgov], "new_device": False, "is_fraud": False, "fraud_scenario": ""})

    # ---- fraud injection ----
    fidx = rng.choice(T, int(T * 0.0025), replace=False)
    scen = rng.choice(["account_takeover", "card_not_present", "atm_skimming"], len(fidx), p=[.4, .4, .2])
    deb.loc[fidx, "amount"] = np.round(deb.loc[fidx, "amount"].to_numpy() * rng.uniform(6, 25, len(fidx)), 2)
    night = start + (((secs[fidx] // 86400) * 86400) + rng.integers(0, 5, len(fidx)) * 3600 + rng.integers(0, 3600, len(fidx))).astype("timedelta64[s]")
    deb.loc[fidx, "ts"] = night
    deb.loc[fidx, "governorate"] = gov_en[rng.integers(0, len(E.GOVERNORATES), len(fidx))]
    deb.loc[fidx, "channel"] = np.where(scen == "atm_skimming", "ATM", np.where(scen == "account_takeover", "InstaPay", "E-commerce"))
    deb.loc[fidx, "category"] = np.where(scen == "atm_skimming", "cash", np.where(scen == "account_takeover", "transfers", "shopping"))
    deb.loc[fidx, "merchant"] = np.where(scen == "atm_skimming", "ATM withdrawal", np.where(scen == "account_takeover", "InstaPay transfer", "Online merchant (overseas)"))
    deb.loc[fidx, ["new_device", "is_fraud"]] = True
    deb.loc[fidx, "fraud_scenario"] = scen
    # card testing bursts
    ct = rng.choice(n, max(1, n // 250), replace=False)     # 400 bursts per 100k customers
    bursts = []
    for c in ct:
        t0 = start + np.timedelta64(int(rng.integers(0, 364 * 86400)), "s")
        k = int(rng.integers(5, 10))
        bursts.append(pd.DataFrame({"customer_id": customers.customer_id.iat[c], "ts": t0 + (rng.integers(0, 900, k)).astype("timedelta64[s]"),
                                    "direction": "debit", "amount": np.round(rng.uniform(5, 50, k), 2), "category": "shopping",
                                    "merchant": "Online merchant (overseas)", "channel": "E-commerce", "governorate": "Abroad",
                                    "new_device": True, "is_fraud": True, "fraud_scenario": "card_testing"}))

    # ---- credits (income) ----
    sec = customers.sector.to_numpy()
    months = pd.date_range(end=pd.Timestamp(AS_OF), periods=12, freq="MS")
    cr = []
    for mo in months:
        day_ = np.where(sec == "Government", 24, np.where(sec == "Private", 26, np.where(sec == "Pension", 1, 10)))
        tsm = np.array([mo + pd.Timedelta(days=int(d) - 1, hours=9) for d in [24, 26, 1, 10]], dtype="datetime64[s]")
        tsx = tsm[np.select([day_ == 24, day_ == 26, day_ == 1], [0, 1, 2], 3)]
        raise_ = np.where((sec == "Government") & (mo >= pd.Timestamp("2026-07-01")), 1.1, 1.0)
        a = income * raise_ * rng.lognormal(0, np.where(sec == "Self-employed", 0.35, 0.03))
        label = np.select([sec == "Government", sec == "Private", sec == "Pension", sec == "Remittance", sec == "Student"],
                          ["Salary - Government", "Salary - Employer", "Pension - NOSI", "Remittance - Gulf", "Family transfer (InstaPay)"], "Client payments")
        cr.append(pd.DataFrame({"customer_id": customers.customer_id.to_numpy(), "ts": tsx, "direction": "credit", "amount": np.round(a, 2),
                                "category": "income", "merchant": label, "channel": np.where(sec == "Student", "InstaPay", "Bank transfer"),
                                "governorate": gov_en[gi], "new_device": False, "is_fraud": False, "fraud_scenario": ""}))
    tx = pd.concat([deb, *bursts, *cr], ignore_index=True)
    tx = tx[tx.ts <= np.datetime64(datetime.combine(AS_OF, datetime.min.time()))].sort_values(["customer_id", "ts"]).reset_index(drop=True)
    tx.insert(0, "txn_id", np.arange(1, len(tx) + 1))
    return tx


def _logins(rng, customers) -> pd.DataFrame:
    act = customers[customers.digital_active]
    cnt = rng.poisson(5, len(act)) * 2
    ci = np.repeat(np.arange(len(act)), cnt)
    T = len(ci)
    start = np.datetime64(AS_OF - timedelta(days=60), "s")
    hw = np.array([1, .5, .3, .2, .2, .3, 1, 2, 3, 3.5, 4, 4, 4, 4, 4, 4, 4, 4.5, 5, 5.5, 6, 5.5, 4, 2]); hw /= hw.sum()
    ts = start + (rng.integers(0, 60, T) * 86400 + rng.choice(24, T, p=hw) * 3600 + rng.integers(0, 3600, T)).astype("timedelta64[s]")
    dev = rng.choice(["Android", "iOS", "Web"], len(act), p=[.78, .18, .04])
    ip = [f"{a}.{b}.{c}.{d}" for a, b, c, d in zip(rng.choice([41, 156, 197], T), rng.integers(1, 255, T), rng.integers(1, 255, T), rng.integers(1, 255, T))]
    df = pd.DataFrame({"customer_id": act.customer_id.to_numpy()[ci], "ts": ts, "device": dev[ci], "ip": ip,
                       "governorate": act.governorate_en.to_numpy()[ci], "success": rng.random(T) < 0.97,
                       "new_device": rng.random(T) < 0.03, "is_attack": False})
    # brute-force / credential stuffing
    atk = []
    for c in rng.choice(act.customer_id.to_numpy(), 300, replace=False):
        k = int(rng.integers(8, 20)); t0 = start + np.timedelta64(int(rng.integers(0, 59 * 86400)), "s")
        atk.append(pd.DataFrame({"customer_id": c, "ts": t0 + np.sort(rng.integers(0, 600, k)).astype("timedelta64[s]"), "device": "Web",
                                 "ip": f"185.{rng.integers(1, 255)}.{rng.integers(1, 255)}.{rng.integers(1, 255)}", "governorate": "Abroad",
                                 "success": np.r_[np.zeros(k - 1, bool), rng.random() < 0.3], "new_device": True, "is_attack": True}))
    return pd.concat([df, *atk], ignore_index=True).sort_values("ts").reset_index(drop=True)


def _holdings(rng, customers, income) -> pd.DataFrame:
    inv = customers[customers.is_investor]
    rows = []
    for ci, seg, sharia, inc in zip(inv.customer_id, inv.segment, inv.sharia_preference, income[inv.customer_id.to_numpy() - 1]):
        uni = [u for u in E.UNIVERSE if (u[7] or not sharia)]
        p_us = 0.4 if seg in ("Affluent", "Private") else 0.15
        w = np.array([p_us if u[3] == "US" else 1 - p_us for u in uni]); w /= w.sum()
        k = int(rng.integers(1, 6))
        pick = rng.choice(len(uni), min(k, len(uni)), replace=False, p=w)
        budget = inc * rng.lognormal(np.log(6), 0.9)
        for j in pick:
            u = uni[j]
            px = u[5] * (48.0 if u[3] == "US" else 1.0)
            qty = max(1, int(budget / k / px))
            rows.append((ci, u[0], qty, round(u[5] * rng.uniform(0.7, 1.2), 2)))
    return pd.DataFrame(rows, columns=["customer_id", "symbol", "qty", "avg_cost"])

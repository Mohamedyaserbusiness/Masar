"""Offline pipeline: generate data -> DQ checks -> DuckDB -> market history -> train forecast + fraud models.
Each step maps 1:1 to a future Airflow task.  Run:  python -m masar.pipeline [--customers 100000]
"""
from __future__ import annotations

import argparse
import json
import time

import duckdb
import pandas as pd

from . import datagen, egypt as E, market_data, ml_forecast, ml_fraud
from .config import DUCKDB_PATH, MODELS_DIR


def dq_checks(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    c, a, tx = t["customers"], t["accounts"], t["transactions"]
    res = []
    def add(name, dim, failed, total):
        res.append({"check": name, "dimension": dim, "failed": int(failed), "total": int(total), "status": "PASS" if failed == 0 else "FAIL"})
    add("customer_id unique", "Uniqueness", c.customer_id.duplicated().sum(), len(c))
    add("email unique", "Uniqueness", c.email.duplicated().sum(), len(c))
    add("phone unique", "Uniqueness", c.phone.duplicated().sum(), len(c))
    add("national ID structure valid", "Validity", sum(not E.validate_national_id(x)[0] for x in c.national_id), len(c))
    add("national ID matches birth date & gender", "Consistency",
        sum((E.nid_birth_gender(n)[0] != b.date()) or (E.nid_birth_gender(n)[1] != g) for n, b, g in zip(c.national_id, c.birth_date, c.gender)), len(c))
    add("phone format (+20 1x)", "Validity", sum(not E.validate_phone(p) for p in c.phone), len(c))
    add("IBAN mod-97 valid", "Validity", sum(not E.validate_iban(i) for i in a.iban), len(a))
    add("income >= sector minimum", "Validity", (c.monthly_income < 500).sum(), len(c))
    add("names not null", "Completeness", c.full_name_ar.isna().sum() + c.full_name_en.isna().sum(), 2 * len(c))
    add("transactions -> customers FK", "Referential integrity", (~tx.customer_id.isin(c.customer_id)).sum(), len(tx))
    add("accounts -> customers FK", "Referential integrity", (~a.customer_id.isin(c.customer_id)).sum(), len(a))
    add("amount > 0", "Validity", (tx.amount <= 0).sum(), len(tx))
    add("txn_id unique", "Uniqueness", tx.txn_id.duplicated().sum(), len(tx))
    return pd.DataFrame(res)


def run(n: int):
    t0 = time.time()
    print(f"[1/5] generating {n:,} Egyptian customers ...")
    t = datagen.generate(n)
    for k, v in t.items():
        print(f"      {k:14s} {len(v):>10,} rows")
    print(f"[2/5] data-quality checks ... ({time.time()-t0:.0f}s)")
    dq = dq_checks(t)
    print(dq[["check", "status", "failed"]].to_string(index=False))
    print(f"[3/5] market history ... ({time.time()-t0:.0f}s)")
    hist = market_data.build_history()
    print(f"[4/5] training forecast model ... ({time.time()-t0:.0f}s)")
    fr = ml_forecast.train(hist)
    print("      walk-forward mean:", fr["report"]["mean"], "| shuffled-label acc:", fr["report"]["shuffled_label_acc"])
    print(f"[5/5] training fraud models ... ({time.time()-t0:.0f}s)")
    rep = ml_fraud.train(t["transactions"], t["customers"])
    print("      fraud:", {k: rep[k] for k in ("pr_auc_lightgbm", "pr_auc_isolation_forest", "precision_at_0.5", "recall_at_0.5")})

    tmp = DUCKDB_PATH.with_suffix(".tmp.duckdb")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    for k, v in {**t, "dq_results": dq, "prices_daily": hist, "forecasts": fr["forecasts"]}.items():
        con.register("v", v); con.execute(f"CREATE TABLE {k} AS SELECT * FROM v"); con.unregister("v")  # nosec B608 - internal table names
    con.execute("CREATE INDEX ix_tx_c ON transactions(customer_id)")
    # aggregates for dashboards / peer benchmarks
    con.execute("""CREATE TABLE peer_benchmark AS
        SELECT c.segment, c.region, t.category, SUM(t.amount)/COUNT(DISTINCT c.customer_id)/12 AS avg_monthly
        FROM transactions t JOIN customers c USING(customer_id) WHERE t.direction='debit' AND NOT t.is_fraud
        GROUP BY 1,2,3""")
    con.execute("""CREATE TABLE agg_monthly AS SELECT date_trunc('month', ts) AS month, direction, COUNT(*) n, SUM(amount) amount
        FROM transactions GROUP BY 1,2 ORDER BY 1""")
    demo = con.execute("""SELECT c.customer_id FROM customers c JOIN (SELECT customer_id, COUNT(*) n FROM transactions GROUP BY 1) x USING(customer_id)
        WHERE c.governorate_en='Cairo' AND c.segment IN ('Mass Affluent','Affluent') AND c.is_investor AND c.digital_active AND c.age BETWEEN 28 AND 45
        ORDER BY x.n DESC LIMIT 1""").fetchone()[0]
    con.execute(f"CREATE TABLE demo_meta AS SELECT {demo} AS demo_customer_id")
    con.close()
    DUCKDB_PATH.unlink(missing_ok=True)
    tmp.rename(DUCKDB_PATH)
    (MODELS_DIR / "pipeline_summary.json").write_text(json.dumps({k: len(v) for k, v in t.items()} | {"seconds": round(time.time() - t0)}, indent=2))
    print(f"done in {time.time()-t0:.0f}s -> {DUCKDB_PATH}  (demo customer {demo})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--customers", type=int, default=100_000)
    run(ap.parse_args().customers)

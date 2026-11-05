"""Export a pseudonymized star schema for Power BI.  Run: python -m masar.powerbi_export
Output: ../powerbi/data/*.parquet (+ small dims as .csv). No names, national IDs, phones or emails leave the bank."""
from __future__ import annotations

import duckdb

from .config import DUCKDB_PATH, JWT_SECRET, ROOT

OUT = ROOT / "powerbi" / "data"

TABLES = {
    "dim_customer": """
        SELECT md5(? || CAST(customer_id AS VARCHAR)) AS customer_key,
               CASE WHEN age < 25 THEN '18-24' WHEN age < 35 THEN '25-34' WHEN age < 45 THEN '35-44'
                    WHEN age < 55 THEN '45-54' WHEN age < 65 THEN '55-64' ELSE '65+' END AS age_band,
               gender, governorate_en AS governorate, region, occupation_en AS occupation, sector, segment,
               CASE WHEN monthly_income < 10000 THEN '< 10k' WHEN monthly_income < 20000 THEN '10-20k'
                    WHEN monthly_income < 40000 THEN '20-40k' WHEN monthly_income < 100000 THEN '40-100k' ELSE '100k+' END AS income_band,
               marital_status, kyc_status, aml_risk, digital_active, is_investor, sharia_preference, preferred_language,
               CASE WHEN credit_score < 550 THEN 'Poor' WHEN credit_score < 650 THEN 'Fair' WHEN credit_score < 750 THEN 'Good' ELSE 'Excellent' END AS credit_band,
               year(customer_since) AS customer_since_year
        FROM customers""",
    "dim_geography": """
        SELECT DISTINCT governorate_en AS governorate, governorate_ar, governorate_code, region FROM customers""",
    "dim_date": """
        SELECT d::DATE AS date, year(d) AS year, month(d) AS month, strftime(d, '%Y-%m') AS year_month,
               strftime(d, '%b') AS month_name, dayofweek(d) AS weekday, strftime(d, '%a') AS weekday_name,
               (d BETWEEN DATE '2026-02-18' AND DATE '2026-03-19') AS is_ramadan,
               (d BETWEEN DATE '2026-03-20' AND DATE '2026-03-23' OR d BETWEEN DATE '2026-05-26' AND DATE '2026-05-30') AS is_eid,
               (dayofweek(d) IN (0,1,2,3,4)) AS egx_trading_day
        FROM range(DATE '2025-11-01', DATE '2026-11-30', INTERVAL 1 DAY) t(d)""",
    "fact_transactions": """
        SELECT txn_id, md5(? || CAST(customer_id AS VARCHAR)) AS customer_key, ts::DATE AS date, hour(ts) AS hour,
               direction, amount, CASE WHEN direction='debit' THEN amount ELSE 0 END AS debit_amount,
               CASE WHEN direction='credit' THEN amount ELSE 0 END AS credit_amount,
               category, merchant, channel, governorate, is_fraud, fraud_scenario
        FROM transactions""",
    "fact_accounts": """
        SELECT md5(? || CAST(customer_id AS VARCHAR)) AS customer_key, type AS account_type, currency, balance, interest_rate FROM accounts""",
    "fact_loans": """
        SELECT md5(? || CAST(customer_id AS VARCHAR)) AS customer_key, loan_type, principal, rate, tenor_months,
               monthly_installment, remaining, days_past_due,
               CASE WHEN days_past_due = 0 THEN 'Current' WHEN days_past_due <= 30 THEN '1-30' WHEN days_past_due <= 60 THEN '31-60'
                    WHEN days_past_due <= 90 THEN '61-90' ELSE '90+' END AS dpd_bucket FROM loans""",
    "fact_certificates": """
        SELECT md5(? || CAST(customer_id AS VARCHAR)) AS customer_key, amount, rate, term_years, start_date::DATE AS start_date, maturity_date::DATE AS maturity_date FROM certificates""",
    "fact_cards": """
        SELECT md5(? || CAST(customer_id AS VARCHAR)) AS customer_key, card_type, credit_limit, outstanding FROM cards""",
    "fact_holdings": """
        SELECT md5(? || CAST(h.customer_id AS VARCHAR)) AS customer_key, h.symbol, h.qty, h.avg_cost FROM holdings h""",
    "fact_logins_daily": """
        SELECT md5(? || CAST(customer_id AS VARCHAR)) AS customer_key, ts::DATE AS date, device,
               COUNT(*) AS logins, SUM(CASE WHEN success THEN 0 ELSE 1 END) AS failed, MAX(is_attack::INT) AS attack_flag,
               MAX(new_device::INT) AS new_device_flag
        FROM login_events GROUP BY 1,2,3""",
    "dim_instrument": """
        SELECT f.symbol, f.last_close, f.prob_up, f.exp_ret_5d, f.p10_5d, f.p90_5d, f.confidence, f.vol_annual, f.mom_3m FROM forecasts f""",
    "fact_prices_daily": """SELECT symbol, date::DATE AS date, open, high, low, close, volume, source FROM prices_daily""",
    "dq_results": "SELECT * FROM dq_results",
}
SMALL = {"dim_geography", "dim_date", "dim_instrument", "dq_results"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    salt = JWT_SECRET[:16]
    for name, sql in TABLES.items():
        params = [salt] if "?" in sql else []
        con.execute(f"COPY ({sql}) TO '{(OUT / f'{name}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)", params)
        if name in SMALL or name == "dim_customer":
            con.execute(f"COPY ({sql}) TO '{(OUT / f'{name}.csv').as_posix()}' (HEADER, DELIMITER ',')", params)
        n = con.execute(f"SELECT COUNT(*) FROM '{(OUT / f'{name}.parquet').as_posix()}'").fetchone()[0]  # nosec B608 - internal paths
        print(f"  {name:20s} {n:>10,} rows")
    con.close()
    print("exported to", OUT)


if __name__ == "__main__":
    main()

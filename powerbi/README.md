# Masar – Power BI pack (bank-side analytics)

Pseudonymized star schema exported from the 100k-customer dataset. **No names, national IDs, phones or emails**: customers are identified only by a salted `customer_key` hash, and ages/incomes are banded (privacy by design, PDPL).

Regenerate any time: `cd backend; ..\.venv\Scripts\python.exe -m masar.powerbi_export`

## 1. Load (≈ 3 min)
1. Power BI Desktop → **Get data → Parquet** → paste the path of each file in `C:\Users\ebi\Downloads\masar\powerbi\data\` (13 files; fact_transactions is 6.5M rows). Small dims also exist as `.csv` if you prefer.
2. Rename queries to the file names (without `.parquet`). In Power Query set `date` columns to **Date** type.
3. View → Themes → Browse → `masar_theme.json`.

## 2. Relationships (Model view, single direction, many-to-one)
| From (many) | To (one) |
|---|---|
| fact_transactions[customer_key], fact_accounts, fact_loans, fact_certificates, fact_cards, fact_holdings, fact_logins_daily | dim_customer[customer_key] |
| fact_transactions[date], fact_logins_daily[date], fact_prices_daily[date] | dim_date[date] |
| dim_customer[governorate] | dim_geography[governorate] |
| fact_holdings[symbol], fact_prices_daily[symbol] | dim_instrument[symbol] |

Mark `dim_date` as date table (Table tools → Mark as date table → `date`).

## 3. Measures
Create table `_Measures` and paste from `measures.dax` (≈45 measures: deposits, NPL, spend MoM/YTD, Ramadan uplift, digital share, fraud bps, failed logins, DQ pass rate…).

## 4. Report pages (spec)
| Page | Visuals |
|---|---|
| **Executive** | Cards: Customers, Total Deposits EGP, Loan Book, NPL Ratio %, Digital Adoption %, Fraud Rate (bps) · line: Spend & Income Inflows by year_month · map/bar: Customers by governorate |
| **Customers & segments** | Donut: segment · stacked bar: age_band × gender · matrix: region × income_band (Customers, Avg Balance) · bar: occupation |
| **Spending behaviour** | Bar: Spend by category · line: Spend by year_month with Ramadan/Eid highlighted (dim_date flags) · KPI: Ramadan Spend Uplift % · bar: top 10 merchants · hour-of-day column chart |
| **Digital & channels** | Stacked column: Spend by channel per month · Digital Channel Share % vs Cash Withdrawal Share % · Logins by device |
| **Fraud & security** | Cards: Fraud Transactions, Fraud Amount, Fraud Rate (bps), Attacked Customers · bar: fraud_scenario · scatter: hour vs amount (is_fraud legend) · Failed Login % trend |
| **Lending & deposits** | Bar: Loan Book by loan_type · column: dpd_bucket · Avg CD Rate · deposits by account_type/currency |
| **Investments** | Bar: Holders by symbol · table: dim_instrument (prob_up, exp_ret_5d, confidence, vol_annual) · line: fact_prices_daily close by symbol (slicer) |
| **Data quality** | Card: DQ Pass Rate % · table: dq_results (check, dimension, failed, total, status) with conditional formatting |

## 5. Row-level security (governance demo)
Modeling → Manage roles → role **Upper Egypt manager**: table `dim_geography`, filter `[region] = "Upper Egypt"` (create similar roles for Delta, Greater Cairo…). Test with *View as*.

Slicers to add on every page: region, governorate, segment, year_month.

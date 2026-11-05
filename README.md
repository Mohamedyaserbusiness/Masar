# Masar (مسار) — Egyptian digital banking + stock intelligence (demo edition)

## Run
```powershell
cd C:\Users\ebi\Downloads\masar
.\run.ps1            # opens API :8000 + web :3000 in two windows, then the browser
```
First run only (already done): `cd backend; ..\.venv\Scripts\python.exe -m masar.pipeline` (≈40 s: 100k customers, 6.5M transactions, models).
Optional real US data: put free keys in `.env` (`FINNHUB_API_KEY` = live trades, `TWELVEDATA_API_KEY` = history), re-run the pipeline, restart.

Demo logins (password `Masar@2026`): `demo@masar.eg` (customer) · `advisor@masar.eg` · `compliance@masar.eg` · `admin@masar.eg`

## What's inside (maps to the 13 requirements)
| # | Feature | Where |
|---|---|---|
| 0, 7 | 100k synthetic **Egyptian** customers: AR/EN names, valid 14-digit national IDs, mod-97 EG IBANs, 27 governorates, EGP incomes ≥ minimum wage, InstaPay/Fawry/Meeza, Ramadan/Eid/summer seasonality, 6.5M transactions, 0.7M logins, injected fraud | `backend/masar/datagen.py`, `egypt.py` |
| 1 | Banking profile: accounts, cards, loans, CDs, KYC/AML, I-Score, masked PII | Home page, `/me/overview` |
| 2 | Suitability-first recommendations: risk quiz → band 1-5 → allocation → stocks (volatility caps, sector diversification, Sharia filter, "customers like you", explanations) | Invest page, `recommend.py` |
| 3 | Live market dashboard over WebSocket (EGX + US + USD/EGP + gold 21K), market hours, candlesticks + forecast band, LIVE/SIMULATED badges | Markets page, `live.py` |
| 4 | LightGBM direction + quantile forecasts, walk-forward validation vs baselines + shuffled-label leak test (honest metrics shown in UI) | `ml_forecast.py`, Staff → Models |
| 5 | Customer analytics: spending by category, income vs spend, daily trend, subscriptions, peer benchmark, financial-health score | Home page |
| 6 | Real-time fraud scoring (rules + IsolationForest + LightGBM) on a live transaction stream → "Was this you?", alert queue; login risk scoring; insider UEBA; governance: catalog, 13 DQ checks, hash-chained audit log, break-glass PII, retention/PDPL | Security, Staff → Fraud / Governance |
| 8 | Sign-up/sign-in: Argon2id, JWT httpOnly cookie, lockout, rate limit, CSRF header, RBAC (customer/advisor/compliance/admin), PDPL consents | `security.py`, Login/Sign-up |
| 9-11 | Competitor research, extra features, senior delivery plan | `docs/ROADMAP.md` |
| 12 | Next.js UI: Arabic/English + RTL, dark mode, hide-balances privacy toggle, responsive | `web/` |
| 13 | Llama 3.2 assistant via local Ollama: intent router + read-only tools on *your own* data, instant exact answers for balances/spending, injection guard | Assistant page, `chat.py` |

## 5-minute demo script
1. **Sign up** (`/signup`) with any Egyptian-format data, e.g. NID `29501120100503`, mobile `01012345678` → dashboard appears instantly (linked to a synthetic history). Show validation errors with a bad NID.
2. **Home**: KPIs, health score, charts, subscriptions, peer comparison; toggle **عربي** (RTL) and the 👁 privacy blur.
3. **Markets**: ticks flash live; open COMI → candles + gold forecast line; point at **Model honesty check** (≈50% on simulated data = no leakage).
4. **Invest**: answer the quiz → band, allocation donut, 6 explained picks; tick Sharia-only.
5. **Assistant**: "كم صرفت على الأكل الشهر اللي فات؟" (instant, exact) → "What is the forecast for COMI?" (Llama, ~10 s, local).
6. **Security**: ⚡ Simulate suspicious transaction → risk 100 with reasons → "No — freeze my card".
7. Log in as **compliance@masar.eg** → Staff: live transaction stream + alert queue, Customer 360 with masked PII → break-glass (asks for justification), Governance: DQ checks + audit chain ✓ (your actions appear in the log), Models.

## Honest limits of this demo
* EGX prices are **simulated** (no legitimate free EGX feed; production = EODHD/ICE licence). US is simulated unless you add free keys.
* Fraud metrics are near-perfect because synthetic fraud is easy to separate; real labels needed in production.
* Today: DuckDB + SQLite + in-process streams. Production plan (Kafka, Spark, Airflow, Postgres/Timescale, Power BI, MFA, Llama Guard, CI/CD) is in `docs/ROADMAP.md`.

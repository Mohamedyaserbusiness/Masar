# Masar (مسار): today's 2-hour demo build, then the full production roadmap

## Part 1: Today's demo build (under 2 hours)

**Context**
- The presentation is in under 2 hours.
- You said "no data engineering needed right now", and also that Spark + Airflow must run live. Both can't fit in 2 hours, so **I'm following "no data engineering right now"**.
- Spark, Airflow, Kafka and Postgres are the first job after the demo (Part 2, phase 4).
- The frontend is **Next.js**, as you chose.
- Everything runs natively on this PC (Docker is off). Every external dependency has an offline fallback, so the demo can't break.

**Stack today**
- **Web:** Next.js + TypeScript + Tailwind, using a portable Node 24 zip (no admin rights needed).
- **API:** FastAPI on a Python 3.14 venv.
- **Data:** DuckDB (100k customers, ~3M transactions) + SQLite (users, audit log, alerts).
- **ML:** LightGBM, IsolationForest, KMeans.
- **LLM:** Ollama `llama3.2:3b`, downloaded in the background.
- **Market data:**
  - Finnhub WebSocket for live US prices (needs a free key).
  - Twelve Data for US history + USD/EGP + gold (needs a free key).
  - A simulator for EGX always (there's no legitimate free EGX feed), and for everything if there are no keys. Simulated data is always labelled SIMULATED.

**Build order.** Each checkpoint leaves a runnable demo.

| Checkpoint | Minutes | Delivers |
|---|---|---|
| A | 0–35 | Scaffold + background installs (pip, Node, npm, Ollama pull) · Egyptian data generator → DuckDB (100k customers: AR/EN names, valid 14-digit national IDs, EG IBANs, 27 governorates, EGP incomes ≥ minimum wage, InstaPay/Fawry/Meeza transactions, Ramadan seasonality, injected fraud) · FastAPI auth (sign-up/in, Argon2, JWT in an httpOnly cookie, roles customer/advisor/compliance/admin, seeded demo users) + profile/accounts/transactions/analytics endpoints |
| B | 35–65 | Next.js: sign-in/up · customer dashboard (profile, balances, spending donut, income vs expense, health score, recent transactions) · AR/EN + RTL toggle · dark mode · live Markets page (WebSocket ticker grid, candlestick chart, market status, LIVE/SIMULATED badges) |
| C | 65–90 | LightGBM direction + quantile forecasts, with a walk-forward comparison against a naive baseline (honest metrics shown) · recommendations (risk quiz → risk band → suitable stocks + "why") · live transaction simulator + fraud scoring (rules + IsolationForest) → staff-console alerts + customer "Was this you?" · login anomaly flags · governance panel (PII catalog, DQ checks, hash-chained audit log) |
| D | 90–110 | Llama assistant (Ollama, AR/EN, tools over the signed-in user's own data, prompt-injection filter, rule-based fallback) · `docs/ROADMAP.md` (Part 2: competitor research, extra features, phases) · 5-minute demo script · smoke test |

If time runs short, I simplify the chatbot polish (D) and the governance panel (C) first. A and B are never cut.

**Your part, in parallel (3 minutes):**
- Create free keys at finnhub.io and twelvedata.com.
- Paste them into `C:\Users\ebi\Downloads\masar\.env` as `FINNHUB_API_KEY=` and `TWELVEDATA_API_KEY=`.
- Without keys, the market runs in labelled simulation.

**Not today (moved to Part 2):** Spark, Airflow, Kafka, Postgres/Timescale, the Power BI pack, Chronos-2, TOTP MFA, Llama Guard, CI/CD, observability, full test suite.

**Verify:**
1. `run.ps1` starts the API on :8000 and the web app on :3000.
2. A smoke script checks `/health`, sign-up/login, `/me/analytics`, the market WebSocket and `/chat`.
3. Demo walk-through: sign up → dashboard → live market ticks → forecast → risk quiz → recommendations → assistant in Arabic and English → trigger a suspicious transaction → alert appears in the staff console → governance/audit view.

---

# Part 2: Full production roadmap (after the demo)

## Context
You asked for one production-grade system covering 13 items:
- 100k synthetic Egyptian bank customers
- live stock streaming
- a banking profile
- stock recommendations
- ML price prediction
- customer analytics
- fraud/anomaly detection + data governance
- sign-up/sign-in with authorization
- a Llama chatbot
- a polished UI
- competitor research, extra feature ideas, and a senior delivery plan

This is greenfield: nothing in `C:\Users\ebi` or `Downloads` can be reused directly. Your earlier projects (`retention_desk`, `nilemart-forecast`, `sales-forecaster`) use FastAPI + pytest + Docker, and we keep those conventions.

**Two calls I'm making as the senior on this project:**
1. **"Production-ready"** here means production-grade engineering: secure, tested, CI/CD, observable, containerized, documented, running on synthetic data. Going live with real Egyptian customers also needs licences and audits that code can't provide (see *Go-live* below).
2. **"High accuracy" stock prediction.** Daily price moves are mostly noise. A model claiming more than ~65–70% next-day direction accuracy out-of-sample is almost always leaking future data.
   - We'll use the strongest current techniques and validate them the way a quant desk would: walk-forward, purged, and compared against naive baselines.
   - Users will see each model's real track record.
   - Realistic target: **52–58% direction accuracy with well-calibrated price ranges.** That is genuinely useful, and the system says so honestly.

**This PC:**
- CPU/RAM/GPU: i7-10700 (8 cores/16 threads), 32 GB RAM, Intel UHD 630 (no CUDA), 116 GB free.
- Docker 29.8 + Compose v5.6 are installed, but the Docker daemon isn't running.
- Ollama is installed natively (only `qwen2.5:7b` pulled).
- No Node.js. Local Python is 3.14; containers will pin 3.12 for ML wheel compatibility.

## Locked decisions
| Topic | Decision |
|---|---|
| Markets *(your choice)* | **EGX**: ~30 most-liquid tickers from Yahoo `.CA`, ~20 min delayed, polled every 60 s. **US**: ~30 large caps/ETFs over the Finnhub free WebSocket (real-time). Also USD/EGP and gold (21K EGP/gram). **No crypto**, which is prohibited without a CBE licence (Law 194/2020 Art. 206). |
| LLM *(your choice)* | **Local only**, with Ollama running natively on Windows: `llama3.1:8b` (answers), `llama3.2:3b` (fast mode/extraction), `llama-guard3:1b` (safety), `bge-m3` (embeddings). No customer data leaves the machine. |
| Frontend *(your choice)* | Next.js (App Router) + TypeScript, bilingual AR/EN with full RTL |
| Data platform *(your choice + mine)* | Kafka + **Spark** (Structured Streaming + batch) + Delta Lake + **Airflow 3**. Postgres 17 (TimescaleDB + pgvector) for serving. **Power BI** on a pseudonymized star schema. |
| Backend | FastAPI modular monolith plus 4 small stream-worker services. Splitting everything into microservices is unnecessary for 1–4 developers. |
| Auth | Built into the API on vetted primitives: Argon2id, JWT + rotating refresh tokens, TOTP MFA, RBAC + Postgres RLS. Login telemetry feeds anomaly detection directly. |
| Location | `C:\Users\ebi\Downloads\masar` ("Masar" is a working name; the brand is configurable) |

## Architecture
```
LIVE SOURCES                     HOT PATH (< 2 s)                                         CLIENT
Finnhub WS (US ticks) ──┐
Yahoo poller (EGX, FX,  ├─► market-ingestor ─► Kafka ─► stream-processor ─► TimescaleDB (ticks + 1m/5m/1h/1d candles via continuous aggregates)
  gold, every 60 s)     │                        │                └─► Valkey pub/sub ─► FastAPI WebSocket ─► Next.js (web + PWA)
Replay (after hours) ───┘                        │
txn-simulator (live txns + logins) ─► Kafka ─────┼─► fraud-scorer (rules + LightGBM + IsolationForest; Valkey online features) ─► alerts/notifications
App actions (transfers, logins, staff access) ───┘
                                                 COLD PATH (minutes → daily, orchestrated by Airflow)
Kafka ─► Spark Structured Streaming ─► Delta bronze ─► Spark batch silver ─► gold ─┬─► Postgres `serving` (features, forecasts, recs, segments)
                                                                                    └─► Postgres `dw` star schema ─► Power BI
Airflow ─► ML training (LightGBM, Chronos-2, Spark ALS/KMeans) ─► MLflow registry (gated promotion) ─► nightly batch scoring
AI: chat module ─► intent router ─► whitelisted tools + RAG (pgvector) ─► Ollama @ host.docker.internal:11434 ─► guardrails ─► SSE stream
Governance: OpenLineage (Airflow + Spark) ─► Marquez · Pandera DQ results · hash-chained audit log · PII catalog
```
- **Kafka topics:** `market.ticks`, `market.quotes.egx`, `bank.transactions`, `auth.events`, `staff.access`, `alerts.fraud`, `alerts.price`, `notifications`, plus `*.dlq`.
- **Message schemas:** versioned Pydantic models in `libs/masar_common`.

## Stack (pin exact latest-stable versions at scaffold time)
| Layer | Choice |
|---|---|
| Web | Next.js + TS, Tailwind v4, shadcn/ui, next-intl (ar/en, RTL), TanStack Query, Zustand, zod, TradingView Lightweight Charts (candles), Recharts; Vitest, Playwright, axe |
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, pwdlib[argon2], PyJWT (EdDSA), pyotp, Valkey-backed rate limits |
| Streaming | Apache Kafka 4 (KRaft) + kafbat Kafka UI, aiokafka workers, Valkey (Redis-compatible, BSD licence) |
| Storage | Postgres 17 `timescale/timescaledb-ha` image (TimescaleDB + pgvector), Delta Lake on a local volume |
| Batch/orchestration | Spark 4 (standalone master + 1 worker), Airflow 3 (LocalExecutor, custom image with JDK + pyspark), OpenLineage → Marquez |
| ML | LightGBM, scikit-learn, Optuna, Chronos-2 (CPU), Spark MLlib (ALS, KMeans), SHAP, split-conformal intervals, MLflow 3, Evidently |
| LLM | Ollama (native): Llama 3.1 8B / 3.2 3B, Llama Guard 3 1B, bge-m3; Prompt Guard 2 86M in a small ONNX CPU sidecar |
| BI | Power BI Desktop → Postgres `warehouse` DB, `dw` schema, read-only `powerbi_reader` user |
| Ops | Compose profiles, Caddy (TLS + security headers), Prometheus + Grafana + Loki + Alloy, GitHub Actions, Trivy, gitleaks, bandit, pip-audit, OWASP ZAP |
| Tooling | uv workspace (manages Python 3.12 alongside your 3.14), ruff, mypy, pytest + testcontainers, pnpm |

## Repository layout (key files to create)
```
masar/
├─ docker-compose.yml          # profiles: core | stream | data | ml | obs
├─ pyproject.toml (uv workspace) · .env.example · scripts/{dev.ps1, smoke.ps1}
├─ web/                        # Next.js: app/[locale]/(auth)/…, (app)/{home,accounts,transactions,insights,invest,markets,goals,alerts,assistant,settings}, staff/…
├─ api/app/modules/{auth,banking,market,invest,recs,analytics,chat,staff,governance,notify}/
├─ services/{market_ingestor/providers/{finnhub_ws,yahoo_poller,eodhd,replay}.py, stream_processor, txn_simulator, fraud_scorer, ai_guard}/
├─ libs/masar_common/          # settings, event schemas, kafka I/O, db session, PII crypto, audit, logging
├─ datagen/                    # Egyptian generator: egypt_reference.py (governorates, names, merchants), customers.py, transactions.py, fraud.py, cli.py
├─ ml/masar_ml/{forecasting,recsys,fraud,segmentation,eval}/ · ml/model_cards/
├─ pipelines/airflow/dags/ · pipelines/spark_jobs/ · infra/{airflow,spark,caddy,grafana,prometheus,loki}/
├─ db/migrations/ (Alembic) · db/init/*.sql (extensions, roles, RLS, hypertables, continuous aggregates)
├─ knowledge_base/{ar,en}/ · powerbi/ · tests/{e2e,load}/ · docs/{adr/, runbooks/, data-dictionary.md, compliance.md}
```

## Requirement-by-requirement design

### Synthetic Egyptian data: 100k customers (opening request + item 7)
- **CLI:** `python -m datagen --customers 100000 --months 12 --seed 42`.
  - Vectorized NumPy/Polars generation → Parquet → Postgres (COPY) + Delta bronze.
  - Runs as Airflow DAG `datagen_load` in ≤ 15 min. A `--profile small` (1k customers) exists for tests.
- **Entities:**
  - Customers, KYC/AML rating, addresses.
  - Accounts (EG IBAN), CDs, cards (tokenized, last 4 digits only), loans.
  - Merchants, ~10–15M transactions, beneficiaries.
  - Devices, ~4M login events.
  - Brokerage accounts, holdings, orders, watchlists, risk questionnaires.
  - Staff users + staff access logs.
- **Egyptian realism:**
  - **Identity:**
    - Arabic + English names from curated lists.
    - 14-digit national IDs consistent with date of birth, gender and governorate (century digit, YYMMDD, governorate code, gender digit).
    - Mobile numbers on 010/011/012/015.
    - Valid 29-character EG IBANs (mod-97).
  - **Geography and income:**
    - All 27 governorates, population-weighted with an urban banking skew.
    - Occupation-based log-normal incomes, floored at the minimum wage (EGP 7,000 private sector, 8,000 public sector from July 2026).
  - **Spending behaviour:**
    - Cash-heavy usage; InstaPay, Meeza, Fawry bills, mobile-wallet top-ups, Gulf remittances.
    - Egyptian merchants coded by MCC; government salary day around the 24th.
    - Hijri-computed Ramadan/Eid seasonality, back-to-school, summer Sahel trips, White Friday.
    - ~13% yearly inflation drift.
    - CD and loan rates set from the CBE policy rate in config.
- **Labelled anomalies:**
  - ~0.2% of transactions: card testing, account takeover (new device + new beneficiary + night-time InstaPay), ATM skimming geo-jump, SIM swap, money-mule fan-in/fan-out.
  - Brute-force/credential-stuffing logins.
  - Staff "bulk profile viewing".
- **Validation:** Pandera schemas check types, ranges, uniqueness, FK integrity, ID/IBAN validity and distribution sanity. An HTML profile report is generated.

### 1) Banking profile
- **Customer view:**
  - KYC tier, masked national ID and phone.
  - Accounts, CDs (maturity timeline), cards (freeze/unfreeze, limits), loans (schedule, days past due), beneficiaries.
  - Transactions (search, filter, category, CSV export), statements.
  - Risk profile, consents, security (MFA, devices, sessions).
- **Staff "Customer 360"** (advisor role, assigned customers only): segment, products, alerts, next-best-action. Churn/CLV is P2.

### 2) Stock recommendation system
1. **Suitability first**, aligned with FRA Decree 57/2024 (risk tolerance, objectives, financial solvency).
   - Inputs: an onboarding questionnaire plus banking-derived features (income stability, savings ratio, debt-to-income, emergency-fund months, age, dependents).
   - Output: a risk band from 1 to 5.
2. **Allocation by band** across bank CDs/money-market, gold, EGX equities and US equities. A conservative band never receives a high-volatility pick.
3. **Ranking:**
   - **Candidates** come from three sources:
     - Spark MLlib implicit ALS ("customers like you" holdings, watchlists, trades)
     - content similarity (sector, beta, volatility, dividend, liquidity)
     - the forecast signal
   - **Ranker:** LightGBM LambdaRank orders the candidates.
   - **Hard constraints:**
     - volatility cap per band
     - ≤ 20% in any single name, sector caps
     - liquidity floor
     - Sharia filter (EGX33 Shariah list)
     - no crypto
   - **Diversification:** MMR re-ranking.
4. **Every card explains "why":** risk fit, diversification benefit, forecast + confidence, plus an educational disclaimer. Save/dismiss feedback is logged for retraining.
5. **Evaluation:** precision@10 and NDCG@10 vs a popularity baseline, coverage, diversity. Zero suitability violations is a unit-tested guarantee.

### 3) Live stock-market dashboard
- **Pipeline:**
  - The ingestor uses provider adapters (`FinnhubWS`, `YahooPoller`, optional paid `EODHD`, `Replay`) behind one interface → Kafka.
  - The stream-processor batch-inserts into a TimescaleDB hypertable; continuous aggregates build the candles.
  - Valkey fans out to the WebSockets, and price alerts are evaluated in-stream.
- **UI:**
  - **Market status, computed DST-aware:**
    - EGX: Sun–Thu ~10:00–14:30 Cairo; configurable because an extension is pending.
    - US: 16:30–23:00 Cairo.
  - **Widgets:** EGX30 and S&P 500 index cards; a live watchlist with tick flashes; a sector heatmap; gainers/losers/most active.
  - **Charts:** candles + volume + indicators, with the forecast band as an overlay.
  - **Extras:** USD/EGP and gold-21K widgets; US news from Finnhub.
- **Badges:** "Delayed ~20 min" on EGX prices. "REPLAY" when weekend/after-hours replay is running, so the demo always works without misleading anyone.

### 4) ML stock prediction: chosen technique
- **Targets:** 1-day and 5-day log returns (P10/P50/P90 quantiles) plus a direction probability. Displayed prices are derived from these.
- **Features:** computed in Spark, point-in-time:
  - return lags, volatility, RSI, MACD, Bollinger %B, ATR, volume z-score
  - market and sector returns, USD/EGP (a key EGX driver), gold, policy rate
  - calendar: Ramadan, EGX holidays, month-end
  - cross-sectional momentum ranks
  - training history: 10+ years of daily bars
- **Models:**
  - **LightGBM global panel model:** a direction classifier + quantile regressors. It is the strongest, most robust option on noisy tabular market data, fast on CPU, and explainable with SHAP.
  - **Chronos-2 foundation model** with covariates. It is top-ranked in the 2026 LiveHouse-TS benchmark and runs zero-shot on CPU, producing multi-horizon probabilistic paths.
  - **Ensemble:** the two are weighted per horizon on validation data, with split-conformal intervals.
  - No pure LSTM: it usually loses to gradient-boosted models at this data size and is slow on CPU. Chronos-2 covers the deep-learning side.
- **Validation:**
  - Walk-forward expanding window, monthly refit, purge + embargo. Optuna tuning happens inside the folds.
  - The last 12 months are an untouched holdout.
  - **Leakage tests:**
    - a shuffled-label run must fall to ~50%
    - every feature timestamp must be ≤ t
    - a planted future-data "canary" feature must be caught
- **Metrics reported:**
  - direction accuracy, AUC, Brier
  - MASE vs random walk, pinball loss, 80% interval coverage
  - an after-fee backtest: Sharpe and max drawdown vs buy-and-hold
- **Promotion gate:**
  - A model is promoted in the MLflow registry only if it beats the random-walk, always-up and historical-quantile baselines.
  - Otherwise the UI labels its forecasts "low confidence".
  - Each symbol's real hit-rate is shown to users.

### 5) Customer analytics dashboard
- **In the app:**
  - spending by category/merchant over time
  - income vs expenses, savings rate, budgets vs actual
  - detected subscriptions/bills
  - 30-day cash-flow forecast + low-balance warning
  - net-worth timeline (accounts + investments − loans)
  - portfolio vs EGX30/S&P 500
  - financial-health score (0–100) with tips
  - anonymized peer benchmarks (k-anonymity ≥ 50)
- **Bank side in Power BI:**
  - **Star schema** in a pseudonymized `dw` schema:
    - dim_date (Hijri/Ramadan/EGX trading-day flags)
    - dim_customer (age/income bands, segment, risk band)
    - dim_geography (governorate → region)
    - dim_merchant/category, dim_channel, dim_product, dim_instrument
    - facts: transactions, monthly balances, holdings, fraud alerts, logins, recommendations, DQ results
  - **Deliverable:** a PBIP project (TMDL semantic model, DAX measures, RLS by region, brand theme) plus a report spec.
    - Report pages: Executive, Segments, Spending, Digital & Security, Fraud, Investments, Data Quality.
    - Fallback: `measures.dax` + a connection guide.

### 6) Anomaly detection: security + data governance
- **Real-time transaction fraud:**
  - **Detectors:**
    - rules: velocity, limits, new beneficiary + high amount + night, geo-jump
    - supervised LightGBM trained on the labelled scenarios
    - Isolation Forest on each customer's deviation from their own behaviour
    - all three read online features from Valkey
  - **Actions:** the fused score leads to allow, step-up OTP, or hold + compliance case. SHAP values and fired rules explain each decision.
  - **Customer prompt:** a "Was this you?" push.
  - **Targets:** PR-AUC on the holdout, precision at a fixed alert budget, p95 latency < 50 ms.
- **Login security:**
  - Risk-based authentication flags new devices, impossible travel, failure bursts and odd hours, then triggers step-up MFA or a lock.
  - A devices/sessions page lets users revoke access.
- **Insider behaviour (UEBA):**
  - Staff access anomalies (e.g., an advisor viewing 200 profiles/hour) raise alerts.
  - Break-glass access requires a reason and is audited.
- **Data anomalies:** Pandera DQ checks on silver/gold; checks on market-feed staleness, spikes and gaps.
- **Governance:**
  - **Catalog:** column-level, with PII/sensitive classification, owner and retention.
  - **Encryption:** AES-GCM field encryption + HMAC blind indexes (national ID, phone). Card numbers (PANs) are never stored.
  - **Access controls:** role-based masking + Postgres RLS.
  - **Audit:** a hash-chained append-only audit log, verified nightly.
  - **Privacy operations:** consent records; export/delete data-subject requests; a retention/anonymization DAG; Marquez lineage; a breach runbook (72 h notice).
- **Regulatory stance:** design to the stricter regime.
  - CBE-supervised banking data is exempt from the PDPL (Art. 3) if CBE rules are followed.
  - FRA-regulated investment activity is covered by the PDPL (executive regulations, Decree 816/2025).
  - We therefore treat financial data as sensitive and keep all data resident in Egypt.

### 8) Sign-up / sign-in, authentication, authorization
- **Sign-up form:**
  - email
  - Egyptian mobile number
  - password (strength check + common/breached-password blocklist)
  - national ID (structure must match date of birth and gender)
  - PDPL consents
- **After sign-up:**
  - email verification (Mailpit in dev)
  - TOTP enrolment (forced for staff)
  - linking to an existing synthetic customer by national ID + OTP, or "demo mode: generate my history"
  - 20 seeded demo users across all roles
- **Tokens:**
  - 15-minute EdDSA JWT access token (JWKS, key rotation).
  - Opaque refresh token in an httpOnly/Secure/SameSite cookie, rotated with reuse detection.
  - CSRF double-submit protection; the Next.js proxy keeps cookies first-party.
- **Abuse protection:** progressive delays + lockout; per-IP and per-user rate limits.
- **Roles:**
  - `customer`
  - `advisor` (assigned customers only)
  - `analyst` (aggregates only)
  - `compliance` (masked PII + audited break-glass)
  - `admin`
- **Enforcement:**
  - Scopes are checked in API dependencies, with Postgres RLS as defense in depth.
  - Every auth event is audited and published to `auth.events`.

### 12) UI/UX
- **Foundation:**
  - mobile-first PWA
  - AR/EN toggle with full RTL mirroring (logical CSS)
  - IBM Plex Sans Arabic + Inter fonts
  - EGP formatting (`ar-EG`/`en-EG`), optional Eastern Arabic digits
  - dark/light themes
- **Comfort:**
  - "hide balances" privacy toggle
  - skeleton loaders and empty states
  - plain-language tooltips ("What's RSI?")
  - "Ask about this" buttons that open the assistant with context
- **Accessibility:** gains/losses use ▲/▼ plus colorblind-safe colors, so meaning never relies on color alone. WCAG 2.2 AA, checked with axe in CI.
- **Flows:** a friendly 6-step risk-questionnaire wizard; a 3-tap paper-trade flow.
- **Pages:**
  - Home · Accounts · Transactions · Insights
  - Invest (portfolio + recommendations) · Markets (live) · Symbol detail
  - Goals · Alerts · Assistant · Settings (security, privacy/consents, data export)
  - `/staff`: Customer 360, Fraud cases, Governance, DQ, Audit, Models, Users

### 13) Llama assistant: local Ollama on CPU
- **Latency on this PC.** The 8B model generates only ~6–9 tokens/s here, so the design works around that:
  - **Instant answers for factual intents** (balance, recent transactions, quote): an intent router (bge-m3 kNN over labelled AR/EN examples) calls whitelisted read-only tools, and the answer is filled into a bilingual template.
  - **Slot extraction:** rules and `dateparser` first; Llama 3.2 3B in JSON mode as a fallback.
  - **Open questions** (explanations, advice framing, RAG answers): Llama 3.1 8B.
  - **Speed-ups:** a stable system-prompt prefix that reuses Ollama's KV cache; `keep_alive=-1`; streaming over SSE.
  - **Expected timing:** first token ~2–5 s once warm; full answer ~10–20 s. "Fast mode" switches to the 3B model.
- **Tools** (all read-only):
  - accounts summary, spending breakdown, transactions
  - portfolio, recommendations, quote/forecast
  - explain alert, FX/gold
  - product FAQ via RAG
- **Safety:**
  - Input: Prompt Guard 2 (injection/jailbreak) + PII redaction.
  - Output: Llama Guard 3 1B + validators (no unmasked numbers, no "guaranteed returns").
  - Tools run with the caller's identity, so cross-customer access is impossible.
  - The LLM can only *draft* actions (e.g., a transfer). The user confirms them with MFA in the UI.
  - RAG answers carry citations; per-user rate and token limits apply.
- **RAG:** a bilingual knowledge base (fictional product docs, fees, FAQs, financial literacy, EGX glossary) → bge-m3 → pgvector + Postgres full-text hybrid search.
- **Batch AI:** Airflow generates nightly "Why is it moving?" stock digests, so the CPU time isn't user-facing.
- **Evaluation:**
  - 150 AR/EN questions with the expected intent, tool and answer facts, plus red-team prompts.
  - Gates: ≥ 90% routing accuracy, 0 cross-user leaks, numeric answers equal to the SQL result.
  - Llama 3.x's Arabic is fair, not native, so UI text uses static i18n and Arabic answers are tested explicitly.

### 9) What live apps do (2026 research) and what we adopt
| App | Notable features | We adopt |
|---|---|---|
| Thndr (EG) | EGX + ADX + US stocks, 34 funds, digital gold (230k+ users), savings/fixed income, AI planning tools, consolidated portfolio; #1 EGX broker by share | Gold + funds/CDs next to stocks; one net-worth view |
| Telda (EG) | Payments + card + EGX trading in one app (Mar 2026), zero commission, national-ID-only fund onboarding (Beltone), redemptions straight to the card | Unified bank + invest + pay; frictionless onboarding |
| InstaPay (CBE) | Instant bank ↔ wallet ↔ Meeza transfers | InstaPay-style transfers in data and flows |
| Robinhood | Cortex AI assistant (portfolio-aware), Cortex Digests ("why a stock moved"), Agentic Trading beta (May 2026) | AI digests; portfolio-aware assistant |
| Revolut | AIR assistant (Apr 2026): spending insights, subscription management, card controls, investment tracking; biometric approval for sensitive actions; robo-advisor | Subscription detector; card controls in chat; approval-gated actions |
| eToro | Tori AI analyst with portfolio memory + social sentiment; ring-fenced "Agent Portfolios"; AI connectors with per-action approval | Paper-trading sandbox; assistant memory; human in the loop |
| Public / Webull | Plain-language AI agents; MCP-based trading | Read-only MCP endpoint (P3) |

**Gaps in the original scope we're adding:**
- gold and fixed income alongside stocks
- subscription and bill management
- AI digests
- human approval for any AI-initiated action
- a paper-trading sandbox
- a consolidated net-worth view
- a Sharia filter
- frictionless onboarding

### 10) Extra features I recommend
| Priority | Features |
|---|---|
| P1 (in v1) | Paper trading (virtual EGP 100k) to try recommendations · price/security alerts + notification center · goals (Hajj/Umrah, wedding, car, home, school fees) · zakat calculator (cash, gold 21K/24K, stocks) · Sharia-compliant mode · financial-health score · subscription & bill detector |
| P2 | Nightly AI stock digests · cash-flow forecast + low-balance warning · peer benchmarks · round-up micro-investing into gold/money-market · advisor next-best-action · churn & CLV (bank side) · drift monitoring (Evidently) |
| P3 | Passkeys (WebAuthn) · Arabic voice input (whisper.cpp) · Monte-Carlo retirement planner · read-only MCP server · credit pre-qualification (synthetic I-Score) |

### 11) Senior delivery plan
Every phase ends with a demo, and its exit criteria must pass before the next phase starts. Estimates assume one developer working with Claude Code. With a team of four (data engineering, ML, backend, frontend), phases 3–7 run in parallel and the whole project takes ~6–7 weeks.

| # | Phase (weeks) | Scope | Exit criteria |
|---|---|---|---|
| 0 | Foundations (1) | Monorepo, compose profiles, Postgres/Valkey/Kafka, API + web shells (i18n/RTL, design system), CI, ADRs | `core` profile healthy; CI green; bilingual shell renders |
| 1 | Data (1–2) | datagen + Pandera + `datagen_load` DAG + data dictionary/catalog | 100k customers and ~12M transactions load in ≤ 15 min; all DQ checks pass |
| 2 | Auth + profile (2–3) | Sign-up/in, MFA, RBAC/RLS, audit; profile/accounts/transactions APIs + UI | e2e sign-up → MFA → profile passes; cross-customer reads return 403/404 |
| 3 | Live market (3–4) | Ingestor, Kafka, Timescale continuous aggregates, WebSocket, live dashboard, replay, alerts | US tick-to-UI p95 < 2 s; EGX refreshes every 60 s; replay works on weekends. **MVP demo** |
| 4 | Lakehouse (4–6) | Spark streaming → Delta; DAGs `market_history_backfill`, `market_eod`, `lake_silver_gold`, `features_daily`, `dw_build`, `dq_governance`; Marquez; Power BI | DAGs green; lineage visible; Power BI refresh + RLS work |
| 5 | ML + recs (6–8) | Forecasting, segmentation (Spark KMeans), risk profiling, recsys; `train_weekly` (gated) + `score_nightly`; model cards; UI | Gates met or forecasts labelled low-confidence; NDCG@10 beats popularity; 0 suitability violations |
| 6 | Security + governance (8–9) | txn-simulator, fraud-scorer, login risk-based auth, UEBA, case management, consents/data-subject requests, retention | Fraud PR-AUC target met; p95 < 50 ms; suspicious-transfer e2e passes |
| 7 | Insights + assistant (9–11) | Insights dashboard, goals/zakat, Ollama assistant, RAG, guardrails, `digests_nightly` | Assistant eval gates pass; first token < 5 s when warm |
| 8 | Hardening (11–13) | Observability, k6 load tests (200 users / 500 WebSockets), ZAP/Trivy/gitleaks, `backup_nightly` + restore drill, docs, a11y audit, VPS deploy guide | All gates green; v1.0 release notes |

**Top risks and mitigations:**
| Risk | Mitigation |
|---|---|
| Yahoo feed breaks or rate-limits | Provider adapters, caching, EODHD swap, replay |
| Accuracy expectations | Promotion gates + per-symbol track record in the UI |
| CPU LLM latency | Router + templates, small prompts, prefix cache, streaming, 3B fast mode |
| RAM pressure (~22 GB with every profile on) | Compose profiles, `.wslconfig` at 18–20 GB, Ollama native |
| Scope creep | P1/P2/P3 tiers + phase gates |
| Hand-built auth | OWASP ASVS L2 checklist, tests, ZAP |

**Working agreements:**
- an ADR for each major decision
- short-lived branches
- conventional commits (I commit only when you ask)
- Definition of Done = tests + docs + passing gates

## Production readiness
- **Security:**
  - OWASP ASVS L2 + API Top 10.
  - Caddy TLS, CSP with nonces, HSTS.
  - Least-privilege DB roles (`app_rw`, `spark_etl`, `powerbi_reader`, `airflow`, `mlflow`).
  - Docker secrets in prod; SBOM.
  - Dependency, container and secret scanning in CI.
- **Reliability:**
  - Health/readiness probes, idempotent consumers, DLQ topics, Spark checkpoints.
  - Nightly backups with a tested restore.
  - SLOs: API p95 < 300 ms, tick-to-UI < 2 s, with Grafana alerts.
- **Testing:**
  - unit
  - integration (testcontainers)
  - contract (OpenAPI)
  - e2e (Playwright)
  - load (k6)
  - ML/data (leakage, Pandera, model gates)
- **Go-live, which needs more than code:**
  - CBE/FRA licensing. Robo-advisory under Decree 57/2024 requires LE 15M capital and quarterly reports.
  - Licensed EGX data with redistribution rights.
  - PCI-DSS.
  - PDPL/CBE compliance + a DPO.
  - An independent penetration test.
  - Hosting inside Egypt.

## One-time setup on this PC (I'll ask before any system-level change)
1. Start Docker Desktop. Set `memory=20GB` in `%UserProfile%\.wslconfig`, which restarts WSL.
2. Install Node 24 LTS (pnpm via corepack) and `uv`.
3. Pull the models: `ollama pull llama3.1:8b llama3.2:3b llama-guard3:1b bge-m3`.
4. Put a free Finnhub API key in `.env`. Get a Hugging Face token and accept the Prompt Guard 2 licence.

## Verification (end-to-end)
1. **Stack:** run `docker compose --profile core --profile stream up -d`. Then `scripts/smoke.ps1` checks every `/health` endpoint, the Kafka topics, and a WebSocket round-trip.
2. **Data:** trigger `datagen_load`. Check row counts, confirm the Pandera report is all green, and spot-check sampled IDs/IBANs.
3. **Tests:** `uv run pytest` (unit + testcontainers), `pnpm test`, and `pnpm e2e` (Playwright). The Playwright scenarios:
   - sign-up → Mailpit verification → MFA → dashboard
   - customer A cannot read customer B's data
   - live ticks move the chart (during US hours or in replay)
   - a suspicious transfer triggers step-up auth and opens a compliance case
   - a conservative user sees only suitable recommendations
   - the assistant answers "كم صرفت على الأكل الشهر اللي فات؟" with the same total the SQL gives
4. **ML:** `airflow dags test train_weekly` → MLflow shows the walk-forward reports vs baselines. Leakage tests pass and model cards are generated.
5. **Load/security:** k6 thresholds pass; ZAP baseline, Trivy and gitleaks come back clean in CI.
6. **Power BI** (manual on your side, since I can't run Power BI Desktop):
   - Connect to `localhost:5432` → `warehouse` as `powerbi_reader`. Disable "Encrypt connection" in dev, or enable Postgres TLS.
   - A refresh should succeed.
   - "View as role" should show the region RLS working.

## Sources
- Thndr: [Forbes ME Fintech 50 2026](https://www.forbesmiddleeast.com/lists/the-middle-easts-fintech-50-2026/thndr/), [product showcase](https://scenenow.com/Business/Thndr-Signals-New-Era-for-Investment-at-Latest-Product-Showcase), [thndr.app](https://thndr.app/)
- Telda: [EGX trading launch](https://egyptianstreets.com/2026/03/31/telda-launches-in-app-securities-trading-and-fund-subscriptions-for-egypts-egx-investors/), [Beltone partnership](https://www.wamda.com/en/2026/06/beltone-teams-telda-expand-digital-investing-access-egypt)
- Robinhood: [Cortex](https://robinhood.com/us/en/support/articles/cortex), [Cortex Digests](https://robinhood.com/gb/en/learn/articles/cortex-digests-is-here), [Synergy26](https://robinhood.com/us/en/newsroom/robinhood-tradepmr-synergy26)
- Revolut: [AIR launch](https://www.revolut.com/news/revolut_enters_new_era_of_money_intelligence_with_launch_of_ai_assistant/), [AIR blog](https://revolut.com/blog/post/air-ai-by-revolut)
- eToro: [Agent portfolios](https://www.financemagnates.com/fintech/etoro-lets-investors-delegate-trades-to-ai-agents-as-automation-usage-nearly-doubles/), [feature summary](https://walnutinvest.com/brokers/etoro); Public/Webull: [comparison](https://www.stork.ai/compare/etoro-vs-public-com), [Webull MCP headline](https://www.streetinsider.com/entities/FDIC/BULL)
- InstaPay: [CBE launch](https://cairoscene.com/Buzz/CBE-Announces-Official-Launch-of-National-Instant-Payment-Network)
- EGX data: [ICE EGX feed](https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx), [EODHD EGX](https://eodhd.com/exchange/EGX?page=3), [Yahoo exchange suffixes](https://scriptagc.wasmer.app/https_help_yahoo_com/kb/finance-for-desktop/SLN2310_html), [borsa (EGX wrapper)](https://github.com/7ashraf/borsa)
- Finnhub WebSocket free tier: [tutorial (May 2026)](https://orthogonal.info/free-real-time-stock-alert-system-finnhub-websockets/)
- EGX hours: [tradinghours.com](https://www.tradinghours.com/exchanges/egx/trading-hours), [extension plan](https://www.arabfinance.com/en/news/newdetails/egx-to-extends-trading-hours-after-eid-el-fitr)
- PDPL: [CMS on executive regulations](https://cms.law/en/are/legal-updates/egypt-s-pdpl-executive-regulations-issued-one-year-compliance-countdown-begins), [Al Tamimi](https://www.tamimi.com/law-update/general/articles/from-policy-to-practice-egypt-issues-executive-regulations-of-the-personal-data-protection-law/), [Law 151/2020 text](https://eg.andersen.com/wp-content/uploads/2025/06/Law-No.-151-OF-2020.pdf)
- FRA robo-advisors: [Decree 57/2024](https://launchbaseafrica.com/2024/05/26/new-robo-advisors-rules-in-egypt-open-opportunities-for-digital-investment-startups), [capital requirement](https://www.egypttoday.com/Article/3/132570/Asset-management-firms-looking-to-use-AI-powered-advisors-require)
- Crypto ban: [Andersen Egypt](https://eg.andersen.com/legality-cryptocurrency-in-egypt/)
- Wages: [EGP 8,000 public (Jul 2026)](https://egyptianstreets.com/2026/04/02/egypt-raises-minimum-wage-to-8000-egp-from-july-2026/), [EGP 7,000 private](https://cairoscene.com/buzz/minimum-wage-for-private-sector-in-egypt-raised-to-egp-7-000); CBE rate: [Trading Economics](https://tradingeconomics.com/egypt/interest-rate/news/596389)
- Forecasting models: [Chronos-2 paper](https://arxiv.org/html/2510.15821v1), [LiveHouse-TS benchmark](https://arxiv.org/pdf/2608.17299)

# CPG Sales Insights — AIA Evaluation Project Build Plan

## Context

**Shrushti** is applying for Sigmoid's internal **AI Acceleration Engineer** role (this machine/account is Sameer's, but the project and submission belong to Shrushti). The evaluation (per `~/Downloads/AIA-Engineer-Evaluation-Project.docx.pdf`) requires building, within 2 weeks, an end-to-end skeleton for a mid-size CPG client: clean data foundation → revenue forecasting → LLM-powered insights → API → simple UI, containerized with CI, tests, and ADRs. **The git history, a methodology spreadsheet, and a 5–10 min video are part of the submission** — so the plan is structured as small, reviewable phases, each ending in a meaningful commit.

User-confirmed decisions:
- **Stack**: FastAPI (API) + Streamlit (UI), all Python
- **LLM**: Gemini by default (free via Sigmoid Google Workspace), behind a pluggable provider interface (+ mock provider for tests/CI)
- **Storage**: DuckDB embedded (analytics-friendly, zero setup); Postgres documented as an extension point
- **Workspace**: new git repo at `~/projects/cpg-sales-insights`
- User's extras: GitHub CI/CD with all stages, mock data, unit + integration tests, Docker, and a **chatbot** as the standout feature

## Working agreement (per user request)
- **After every phase**: I stop and report in plain language — what was built, which files, and exact commands for Shrushti to test it end to end herself. We only move to the next phase after an explicit go-ahead.
- Spell out acronyms and domain terms on first use (e.g., POS = point of sale, the store register / online checkout systems that produce transaction records).
- Each checkpoint is also the natural moment to update `methodology/time-log.md` for the required spreadsheet.

## Architecture

```
data/raw (generated mock CSVs/JSON, with injected quality issues)
   │  ingestion pipeline: extract → validate → clean/normalize → dedupe → load
   ▼
DuckDB (star schema: fact_sales + dim_product + dim_store/region) + data-quality report
   │                                  │
   ▼                                  ▼
Forecasting service                LLM insights service (provider interface:
(scikit-learn linear model w/      Gemini | mock; NL summaries + Q&A over
seasonality features, CIs)         data via safe, whitelisted SQL/metrics)
   └────────────┬─────────────────────┘
                ▼
        FastAPI (REST: /health /metrics /forecast /summary /chat /data-quality)
                ▼
        Streamlit UI (KPI dashboard, forecast explorer, chatbot tab)
```

## Repo layout

```
cpg-sales-insights/
├── src/cpg_insights/
│   ├── data_gen/        # mock data generator (seeded, quality issues injected)
│   ├── pipeline/        # extract.py, validate.py, transform.py, load.py, run.py
│   ├── db/              # DuckDB connection, schema DDL, query helpers
│   ├── forecasting/     # features.py, model.py (train/predict/persist)
│   ├── llm/             # base.py (provider interface), gemini.py, mock.py, insights.py
│   └── api/             # FastAPI app, routers, schemas (pydantic)
├── ui/app.py            # Streamlit dashboard + chatbot
├── tests/unit/  tests/integration/
├── docs/adr/  docs/extension-guide.md  docs/brief/ (copies of the 3 source files)
├── data/raw/ data/processed/ (gitignored except .gitkeep + small sample)
├── Dockerfile  docker-compose.yml  Makefile  .env.example
├── .github/workflows/ci.yml
└── README.md  CLAUDE.md  methodology/ (time log notes → final .xlsx)
```

## Build phases (each = 1+ commits)

### Phase 0 — Workspace & scaffold
- `mkdir -p ~/projects/cpg-sales-insights`, `git init`, copy the 3 brief files into `docs/brief/`
- `pyproject.toml` (uv or pip; deps: fastapi, uvicorn, streamlit, duckdb, pandas, scikit-learn, google-genai, pydantic-settings, pytest, pytest-cov, httpx, ruff)
- Repo skeleton above, `.gitignore`, `.env.example` (`GEMINI_API_KEY`, `LLM_PROVIDER=gemini|mock`), `Makefile` targets: `setup`, `data`, `pipeline`, `train`, `api`, `ui`, `test`, `lint`, `docker-up`
- Start `methodology/time-log.md` immediately (feeds the required .xlsx)

### Phase 1 — Mock data generator
- Seeded generator producing the brief's data landscape: `sales_transactions` from **two simulated point-of-sale (POS) sources with schema drift** — e.g., a store-register feed and an e-commerce feed with different column names/date formats — plus `product_master`, `store_regions`
- Inject realistic issues: nulls, mixed date/currency formats, duplicate retries, negative quantities, unknown SKUs, late-arriving records
- ~50k transactions over 24 months with seasonal + category/region patterns baked in (so the model has real signal to learn)

### Phase 2 — Ingestion pipeline (all stages explicit)
- Discrete, individually-testable stages: **extract** (multi-source readers, schema mapping) → **validate** (rule-based checks, quarantine bad rows) → **transform** (normalize currency/dates/units) → **dedupe** → **load** (DuckDB star schema)
- Emit a **data-quality report** (rows in/out, rejects by rule) — persisted and exposed via API/UI; this is a standout differentiator
- CLI entrypoint: `python -m cpg_insights.pipeline.run`

### Phase 3 — Forecasting
- Feature engineering: month/seasonality (sin/cos), category, region, lagged revenue
- scikit-learn Ridge/LinearRegression per the brief's "linear regression that works beats a neural net that doesn't"; report MAE/MAPE on a holdout split; persist model artifact
- Predict endpoint contract: category + region + horizon → forecast with simple confidence interval
- **Anomaly detection**: z-score check on monthly revenue per category/region; flagged anomalies persisted for the dashboard and LLM commentary

### Phase 4 — LLM insights + chatbot brain
- `LLMProvider` interface (`generate(prompt) -> str`); `GeminiProvider` (google-genai SDK), `MockProvider` (deterministic, used in tests/CI — keeps CI green without secrets)
- Insights service: (a) NL summary of trends from aggregate queries; (b) **Q&A**: question → LLM picks from a whitelisted set of parameterized queries/metrics (no raw SQL execution from LLM output — safe-by-design, worth an ADR) → results → LLM phrases the answer
- **"Explain this forecast"**: LLM function that turns a forecast's inputs/drivers (seasonality, trend, category/region history) into a plain-English explanation
- **Anomaly commentary**: one-line LLM explanation for each flagged anomaly
- Graceful degradation when no API key: clear message, mock fallback

### Phase 5 — FastAPI
- Routers: `/health`, `/metrics/summary`, `/forecast`, `/forecast/explain`, `/insights/summary`, `/chat`, `/data-quality`, `/anomalies`, and `/ingest/upload` (accepts a CSV and runs it through the live pipeline); pydantic request/response schemas; thin routes delegating to services
- FastAPI's auto-generated interactive API docs at `/docs` — linked from README and UI

### Phase 6 — Streamlit UI
- Tab 1: KPI dashboard (revenue by category/region/month, charts) + data-quality panel + **anomaly highlights with LLM one-liners**
- Tab 2: forecast explorer (pick category/region/horizon → chart with CI band) + **"Explain this forecast" button**
- Tab 3: **chatbot** (`st.chat_message` history, calls `/chat`)
- Tab 4 (or sidebar): **"Upload CSV"** widget pushing a file through the live pipeline via `/ingest/upload`, showing the resulting data-quality report — the live-demo moment for the video
- UI talks to the API over HTTP (not direct DB) — clean separation for the demo story

### Phase 7 — Tests (alongside, not after — but consolidated hardening pass here)
- Unit: generator determinism, each pipeline stage (incl. bad-data cases), feature engineering, model sanity (beats naive baseline), LLM service with MockProvider, API routes via `TestClient`
- Integration: full pipeline on small fixture dataset → DuckDB → train → API end-to-end (`/forecast`, `/chat` with mock LLM)
- Target >60% coverage (JD bar), enforced in CI

### Phase 8 — Docker
- Multi-stage `Dockerfile` (builder → slim runtime); `docker-compose.yml` with `api` + `ui` services, shared volume for DuckDB file, healthchecks
- `make docker-up` → seeded data + pipeline + trained model on first boot so a cold evaluator gets a working demo in one command

### Phase 9 — CI (GitHub Actions, all stages)
- `ci.yml` stages: **lint (ruff) → unit tests → integration tests → coverage gate (60%) → docker build → smoke test** (compose up, curl `/health`); LLM_PROVIDER=mock in CI
- Push repo to GitHub (`gh repo create`) so CI actually runs — confirm with user before creating the remote repo

### Phase 10 — Docs & handoff polish
- `README.md`: quickstart (one command), **Mermaid architecture diagram**, link to `/docs` API reference, env vars, troubleshooting
- **3 ADRs**: (1) DuckDB over Postgres, (2) pluggable LLM provider + whitelisted-query chat safety, (3) linear model over complex ML
- `docs/extension-guide.md`: swap to Postgres, add real POS source, add LLM provider, productionize CI/CD — mapped to the brief's "extension points" requirement
- `CLAUDE.md` for the repo (also evidences structured AI methodology)

## Standout extras (all committed scope, integrated into the phases above)
- **Data-quality report** surfaced in API + UI (Phase 2) — evaluators see the messy data being handled, not just the clean result
- **Safe chatbot design** (LLM never executes raw SQL; whitelisted parameterized queries) — strong ADR material (Phase 4)
- **Forecast confidence bands** + holdout MAE/MAPE shown honestly (Phase 3)
- **Anomaly highlights**: z-score detection on monthly revenue (Phase 3), shown on the dashboard with an LLM-written one-line explanation (Phases 4/6)
- **"Explain this forecast" button**: LLM describes the drivers in plain English next to the chart (Phases 4/6)
- **"Upload CSV" in the UI** pushing a file through the live pipeline (Phases 5/6) — the live-demo moment for the video
- **One-command cold start** (`make docker-up` seeds data, runs pipeline, trains model) (Phase 8)
- **Mermaid architecture diagram** in README + FastAPI's free interactive API docs at `/docs` (Phase 10)

Deliberately skipped (scope discipline, the brief penalizes maximum-code): auth, Kubernetes, model registry, streaming ingestion — all listed in the extension guide instead.

## Deliverable support (not code, but on the critical path)
- Commit discipline: small commits with messages reflecting generate→review→refactor loops (git history is scored)
- `methodology/time-log.md` updated each session → converted to the required 3-sheet `.xlsx` (Time Log / Tool Usage Summary / Decision Log) at the end
- Video demo outline drafted in `docs/` once the system runs end-to-end

## Verification
- `make setup && make data && make pipeline && make train && make test` — all green, coverage ≥60%
- `make docker-up` → open Streamlit at `localhost:8501`: dashboard renders real aggregates, forecast chart responds, chatbot answers a data question (mock + Gemini if key present); `curl localhost:8000/health` and `/forecast`
- Cold-start test: clone into temp dir, follow README only, confirm it runs
- Push to GitHub → CI pipeline passes all stages

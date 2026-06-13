# Time Log — AIA Evaluation Project

> This feeds the required methodology spreadsheet (3 sheets: Time Log, Tool Usage Summary, Decision Log).
> Log each session as you go — it's much easier than reconstructing at the end.

## Format
| Date | Duration | Area | AI Tool | What AI Generated | What I Changed/Overrode |
|------|----------|------|---------|-------------------|------------------------|

## Sessions

| Date | Duration | Area | AI Tool | What AI Generated | What I Changed/Overrode |
|------|----------|------|---------|-------------------|------------------------|
| 2026-06-13 | ~1h | Planning + Scaffold | Claude Code | Full architecture plan, all scaffold files, pyproject.toml, Makefile, .env.example | Confirmed all choices; added cheap extras (anomaly highlights, forecast explain, CSV upload, Mermaid diagram) |
| 2026-06-13 | ~30m | DevOps — CI setup + GitHub push | Claude Code | GitHub Actions ci.yml (4 stages: lint→unit→integration→docker), gh CLI install, repo creation | Caught that workflow scope was missing from gh auth — had to re-authenticate manually; AI didn't anticipate this |
| 2026-06-13 | ~10m | Fix — lint errors | Claude Code | Auto-fixed 3 ruff errors (import ordering in config.py + conftest.py, unused pytest import) | No override needed; ran make lint locally, confirmed clean before pushing |
| 2026-06-13 | ~45m | Phase 1 — Mock data generator | Claude Code | generate.py (50k transactions, 2 source feeds, seasonal patterns), products.py (36 SKUs / 5 categories), stores.py (25 stores / 5 regions), 16 unit tests | Overrode: AI used Indian city names for stores (good regional flavour, kept it); AI added unused math import and long lines — caught by lint and fixed; added per-file ruff ignore for seed data files |
| 2026-06-13 | ~15m | Fix — CI unit test failure | Claude Code | Identified root causes: no tests committed yet + coverage gate on wrong step; fixed ci.yml (removed --cov-fail-under from unit step, moved gate to integration step over full suite); added test_config.py as baseline unit test; removed global --cov-fail-under from pyproject.toml | Overrode AI's initial placement of coverage gate — wrong to enforce 60% on a partial test run |
| 2026-06-13 | ~10m | Analysis — CI Integration + Docker failures | Claude Code | Diagnosed: Integration fails because generate.py/pipeline/model not committed (Phase 1 local only); Docker skipped because it depends on integration passing (GitHub Actions "needs" chain) | No fix yet — these will auto-resolve once Phase 1 is committed. Root cause: CI was written for the full system before the system existed. |
| 2026-06-13 | ~1h | Phase 2 — Ingestion pipeline | Claude Code | 5 pipeline stages (extract, validate, transform, dedupe, load), DuckDB star schema (fact_sales + 4 dims + quality report table), 20 unit tests per stage | Overrode: AI used executescript (SQLite API) — DuckDB doesn't have it, caught and fixed immediately; ruff auto-fixed 7 import/style issues |
| 2026-06-13 | ~45m | Phase 2 — Enhancements: quarantine table + 4 new validation rules + 3 ADRs + extension guide | Claude Code | Added rejected_transactions quarantine table (full row as JSON), 4 new rules (invalid_price, zero_price, invalid_date, date_out_of_range), first-rule-wins rejection tagging, 3 ADRs (star schema, LLM interface, chatbot safety), extension guide | Fixed hidden dead-code bug in validate loop; cleaned up redundant line in date_out_of_range rule AI generated |
| 2026-06-14 | ~20m | Phase 2 — End-to-end verification | Claude Code | Ran full pipeline on clean slate: 50,650 rows extracted → 2,641 quarantined → 47,388 loaded into fact_sales; verified all 6 DuckDB tables (dim_product 35 SKUs, dim_store 25 stores, dim_date 731 days, fact_sales 47,388 rows, pipeline_runs 1 run, rejected_transactions 2,641 rows); 46/46 unit tests pass, 71% coverage, ruff lint clean | No overrides — all results matched expectations exactly |
| 2026-06-14 | ~1h | Phase 3 — Forecasting model + anomaly detection | Claude Code | features.py (time/seasonality/lag engineering), model.py (Ridge regression, holdout eval, ±1.96σ CI, multi-step autoregressive predict), anomaly.py (z-score detection, severity tiers, DB persist), train.py (CLI: train + detect in one command); 2 new DB tables (anomalies, model_metrics); 17 unit tests; MAE 171.61, MAPE 14.8%, 17 anomalies detected | Caught bug: severity column not added to DataFrame before final column select — fixed; fixed 5 lint issues (long lines, datetime.UTC alias, import ordering) |

## Key Decisions Log

| Decision | Options Considered | Why Chosen | AI Suggestion | Followed AI? |
|----------|--------------------|------------|---------------|--------------|
| Backend framework | FastAPI vs Django vs Flask | FastAPI: async, auto-docs at /docs, pydantic validation, fast to scaffold | FastAPI | Yes |
| UI framework | Streamlit vs React | Streamlit: all-Python, chat widget built-in, minimal boilerplate for a skeleton | Streamlit | Yes |
| Storage | DuckDB vs PostgreSQL | DuckDB: zero setup, file-based, excellent for analytics queries; Postgres = extension point | DuckDB | Yes |
| LLM provider | Gemini vs Claude vs mock | Gemini: free via Sigmoid Google Workspace; mock for CI/tests; abstracted behind interface | Gemini + mock | Yes |
| ML model | Linear/Ridge vs complex | "Linear regression that works beats a neural network that doesn't" (brief's own words) | Linear/Ridge | Yes |
| Chat safety | Raw SQL from LLM vs whitelisted queries | Never let LLM write/execute raw SQL; use whitelisted parameterized queries | Whitelisted | Yes (overrode naive approach) |
| GitHub auth scope | Default gh auth vs workflow scope | CI pushes .github/workflows/ files which need explicit workflow scope — GitHub blocks it otherwise | Claude didn't know upfront; discovered during push failure | No — had to manually re-auth with -s workflow flag |

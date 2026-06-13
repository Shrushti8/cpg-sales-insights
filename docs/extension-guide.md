# Extension Guide

This document tells the project team how to extend each layer of the system. Each section maps to a specific area of the codebase.

---

## 1. Add a new data source

**File to change:** `src/cpg_insights/pipeline/extract.py`

Add a reader function following the pattern of `extract_pos()` or `extract_ecom()`. It must return a DataFrame with exactly the columns in `UNIFIED_COLS`. The validate/transform/dedupe/load stages are source-agnostic and need no changes.

```python
def extract_warehouse(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df.rename(columns={"wh_txn_id": "transaction_id", ...})
    df["source"] = "warehouse"
    df["channel"] = "b2b"
    return df[UNIFIED_COLS]
```

Then add a call to `extract_all()` in the same file.

---

## 2. Add a new validation rule

**File to change:** `src/cpg_insights/pipeline/validate.py`

Write a function matching the signature `(df: pd.DataFrame, **kwargs) -> pd.Series` returning True for invalid rows. Add it to the `RULES` list in the priority order you want (the first matching rule names the rejection reason).

```python
def _rule_price_spike(df: pd.DataFrame, **_) -> pd.Series:
    """Flag prices more than 10x the median — likely a data entry error."""
    price = df["unit_price"].apply(_try_parse_price)
    median = price.median()
    return price > median * 10

RULES.append(("price_spike", _rule_price_spike))
```

---

## 3. Reprocess quarantined records

**Table:** `rejected_transactions` in DuckDB

Each rejected row is stored with its full original data as JSON and the rule that caught it. To fix and re-ingest:

```python
import json, duckdb, pandas as pd
conn = duckdb.connect("data/processed/cpg.duckdb")
quarantine = conn.execute(
    "SELECT raw_data FROM rejected_transactions WHERE rejection_reason = 'null_store'"
).fetchdf()
rows = [json.loads(r) for r in quarantine["raw_data"]]
# fix the rows, then pass through validate → transform → dedupe → load_facts
```

---

## 4. Swap DuckDB for PostgreSQL

**Files to change:** `src/cpg_insights/db/connection.py`, `src/cpg_insights/db/schema.py`

1. Replace `duckdb.connect()` with a `psycopg2` or `SQLAlchemy` connection
2. Change `INSERT OR REPLACE` → `INSERT ... ON CONFLICT DO UPDATE` (PostgreSQL syntax)
3. Update `DB_PATH` env var → `DATABASE_URL` connection string

The pipeline stages, API, and UI reference only the connection object and do not need changes.

---

## 5. Add a new LLM provider

**Files to change:** `src/cpg_insights/llm/`

1. Create `src/cpg_insights/llm/your_provider.py` with a class implementing `generate(prompt: str) -> str`
2. Register it in `src/cpg_insights/llm/__init__.py`
3. Set `LLM_PROVIDER=your_provider` in `.env`

See ADR 002 for the full rationale.

---

## 6. Add a new chatbot question type

**File to change:** `src/cpg_insights/llm/query_templates.py` (to be created in Phase 4)

Each template is a dict with: `name`, `description` (what the LLM uses to match), `sql` (parameterised), and `param_schema`. No other code changes needed.

---

## 7. Add a new API endpoint

**Files to change:** `src/cpg_insights/api/routers/`

Add a new router file, add the route, import and register it in `src/cpg_insights/api/app.py`. FastAPI auto-generates the `/docs` OpenAPI documentation — no manual docs update needed.

---

## 8. Productionise CI/CD

**File to change:** `.github/workflows/ci.yml`

Current pipeline: lint → unit tests → integration tests → docker build + smoke test.

To productionise, add after docker build:
- Push image to a container registry (ECR, GCR, Docker Hub)
- Deploy to the target environment (ECS, Cloud Run, Kubernetes)
- Run a post-deploy smoke test against the live URL

---

## 9. Improve the forecasting model

**File to change:** `src/cpg_insights/forecasting/model.py`

The current model is a Ridge regression with seasonality features. To improve:
- Add more features (promo flags, weather, competitor pricing)
- Swap the estimator (e.g. `XGBRegressor`, `LightGBM`) — the `train()` / `predict()` interface stays the same
- Add a model registry (MLflow) to version and compare runs

See ADR (planned) for the model choice rationale.

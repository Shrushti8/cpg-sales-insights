# CLAUDE.md — CPG Sales Insights

## Project overview
End-to-end CPG (consumer packaged goods) sales analytics skeleton for the Sigmoid AIA Engineer evaluation. Built with Claude Code.

## Architecture
```
Mock data (data_gen) → Ingestion pipeline (pipeline) → DuckDB star schema (db)
                                                             ↓
                                             Forecasting (scikit-learn Ridge)
                                             LLM insights (Gemini / mock)
                                                             ↓
                                              FastAPI (src/cpg_insights/api)
                                                             ↓
                                              Streamlit UI (ui/app.py)
```

## Key design rules
- LLM never executes raw SQL. Chat uses a whitelisted set of parameterized queries → results → LLM phrases the answer.
- DuckDB is the single data store (file at `data/processed/cpg.duckdb`). Connection helper: `src/cpg_insights/db/connection.py`.
- LLM is behind a `LLMProvider` interface (`src/cpg_insights/llm/base.py`). Switch provider via `LLM_PROVIDER` env var.
- `LLM_PROVIDER=mock` is always available — no API key required. CI always uses mock.

## Dev workflow
```bash
make setup       # install deps + copy .env.example → .env
make data        # generate mock data in data/raw/
make pipeline    # ingest, validate, clean, load into DuckDB
make train       # train revenue forecasting model
make api         # start FastAPI at localhost:8000
make ui          # start Streamlit at localhost:8501
make test        # run all tests with coverage
make docker-up   # one-command full stack (does data+pipeline+train automatically)
```

## Adding a new LLM provider
1. Create `src/cpg_insights/llm/your_provider.py` implementing `LLMProvider.generate(prompt) -> str`
2. Register it in `src/cpg_insights/llm/__init__.py`
3. Set `LLM_PROVIDER=your_provider` in `.env`

## Adding a new data source
1. Add a reader in `src/cpg_insights/pipeline/extract.py`
2. Add source-specific schema mapping in `extract.py`
3. The validate/transform/load stages are source-agnostic — no changes needed there

## Environment variables
See `.env.example` for the full list and descriptions.

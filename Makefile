.PHONY: setup data pipeline train api ui test lint docker-up docker-down clean

PYTHON := .venv/bin/python
UV := $(shell which uv 2>/dev/null || echo uv)
SRC := src

# ── Setup ──────────────────────────────────────────────────────────────────────
setup:
	$(UV) venv --python 3.11 .venv
	$(UV) pip install -e ".[dev]"
	cp -n .env.example .env || true
	mkdir -p models data/raw data/processed

# ── Data & pipeline ───────────────────────────────────────────────────────────
data:
	$(PYTHON) -m cpg_insights.data_gen.generate

pipeline:
	$(PYTHON) -m cpg_insights.pipeline.run

# ── Model training ────────────────────────────────────────────────────────────
train:
	$(PYTHON) -m cpg_insights.forecasting.train

# ── Run services ──────────────────────────────────────────────────────────────
api:
	.venv/bin/uvicorn cpg_insights.api.app:app --host 0.0.0.0 --port 8000 --reload

ui:
	.venv/bin/streamlit run ui/app.py --server.port 8501

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	.venv/bin/ruff check $(SRC) tests

lint-fix:
	.venv/bin/ruff check --fix $(SRC) tests

test:
	.venv/bin/pytest tests/

test-unit:
	.venv/bin/pytest tests/unit/

test-integration:
	.venv/bin/pytest tests/integration/

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker-compose up --build

docker-down:
	docker-compose down -v

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov dist build *.egg-info
	rm -f data/raw/*.csv data/raw/*.json data/processed/*.duckdb models/*.pkl

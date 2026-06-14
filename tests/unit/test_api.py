"""Unit tests for Phase 5 — FastAPI routes via TestClient."""

import io

import pytest
from fastapi.testclient import TestClient

from cpg_insights.api.app import app
from cpg_insights.api.deps import get_conn, get_llm
from cpg_insights.db.connection import get_connection
from cpg_insights.llm.mock import MockProvider

# ── Test DB fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_client(tmp_path_factory):
    """TestClient wired to a small in-memory DuckDB and MockProvider."""
    db_path = tmp_path_factory.mktemp("api") / "test.duckdb"
    conn = get_connection(str(db_path))

    # Seed dimensions
    conn.executemany("INSERT INTO dim_product VALUES (?,?,?,?,?,?,?)", [
        ["P1", "Sunscreen SPF50", "Personal Care", "BrandX", "100ml", 150.0, "2020-01-01"],
        ["P2", "Water 1L", "Beverages", "BrandY", "1L", 35.0, "2020-01-01"],
    ])
    conn.executemany("INSERT INTO dim_store VALUES (?,?,?,?,?,?)", [
        ["ST1", "Store1", "North", "Delhi", "Delhi", "Urban"],
        ["ST2", "Store2", "South", "Chennai", "TN", "Urban"],
    ])

    # Seed fact_sales (10 months × 2 SKUs × 2 stores)
    rows = []
    tid = 0
    for month in range(1, 11):
        d = f"2024-{month:02d}-15"
        for sku, base in [("P1", 150.0), ("P2", 35.0)]:
            for store in ["ST1", "ST2"]:
                tid += 1
                qty, price = 3, base + month
                rows.append([f"T{tid:05d}", d, store, sku, qty, price, qty * price, "pos", "store"])
    conn.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?)", rows)

    # Seed pipeline_runs
    conn.execute("""
        INSERT INTO pipeline_runs VALUES (
            'run-1', '2024-01-01 00:00:00+00', 'combined',
            1000, 900, 100, '{"null_sku": 50, "null_store": 50}'
        )
    """)

    # Seed anomalies
    conn.execute("""
        INSERT INTO anomalies VALUES (
            'a1', '2024-01-01 00:00:00+00', '2024-07-01',
            'Beverages', 'North', 95000.0, 3.2, 'severe',
            'Revenue spike 65% above group mean'
        )
    """)

    mock_llm = MockProvider()

    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[get_llm] = lambda: mock_llm

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    conn.close()


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Metrics ───────────────────────────────────────────────────────────────────

def test_metrics_summary_status(api_client):
    r = api_client.get("/metrics/summary")
    assert r.status_code == 200


def test_metrics_summary_has_categories(api_client):
    r = api_client.get("/metrics/summary")
    cats = {c["category"] for c in r.json()["by_category"]}
    assert {"Personal Care", "Beverages"} == cats


def test_metrics_summary_has_regions(api_client):
    r = api_client.get("/metrics/summary")
    regions = {c["region"] for c in r.json()["by_region"]}
    assert {"North", "South"} == regions


def test_metrics_summary_has_top_skus(api_client):
    r = api_client.get("/metrics/summary")
    assert len(r.json()["top_skus"]) > 0


# ── Forecast ──────────────────────────────────────────────────────────────────

def test_forecast_returns_horizon_rows(api_client, tmp_path):
    # Train a model first
    from cpg_insights.forecasting.model import train
    model_path = tmp_path / "m.pkl"
    conn = get_connection(str(tmp_path / "train.duckdb"))
    conn.executemany("INSERT INTO dim_product VALUES (?,?,?,?,?,?,?)", [
        ["P1", "Sunscreen SPF50", "Personal Care", "BrandX", "100ml", 150.0, "2020-01-01"],
        ["P2", "Water 1L", "Beverages", "BrandY", "1L", 35.0, "2020-01-01"],
    ])
    conn.executemany("INSERT INTO dim_store VALUES (?,?,?,?,?,?)", [
        ["ST1", "Store1", "North", "Delhi", "Delhi", "Urban"],
        ["ST2", "Store2", "South", "Chennai", "TN", "Urban"],
    ])
    rows = []
    tid = 0
    for month in range(1, 11):
        d = f"2024-{month:02d}-15"
        for sku, base in [("P1", 150.0), ("P2", 35.0)]:
            for store in ["ST1", "ST2"]:
                tid += 1
                qty, price = 3, base + month
                rows.append([f"T{tid:05d}", d, store, sku, qty, price, qty * price, "pos", "store"])
    conn.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?)", rows)
    train(conn, holdout_months=2, model_path=model_path)

    import cpg_insights.config as cfg
    original = cfg.settings.model_path
    cfg.settings.__dict__["model_path"] = str(model_path)

    r = api_client.post(
        "/forecast", json={"category": "Personal Care", "region": "North", "horizon": 3}
    )
    cfg.settings.__dict__["model_path"] = original
    conn.close()

    assert r.status_code == 200
    data = r.json()
    assert len(data["forecast"]) == 3
    for pt in data["forecast"]:
        assert pt["lower_bound"] <= pt["predicted_revenue"] <= pt["upper_bound"]


def test_forecast_unknown_category_returns_422(api_client):
    import cpg_insights.config as cfg
    cfg.settings.__dict__["model_path"] = "nonexistent.pkl"
    r = api_client.post("/forecast", json={"category": "Fake", "region": "North", "horizon": 2})
    cfg.settings.__dict__["model_path"] = "models/revenue_model.pkl"
    assert r.status_code in (422, 503)


# ── Insights / Chat ───────────────────────────────────────────────────────────

def test_insights_summary_returns_string(api_client):
    r = api_client.get("/insights/summary")
    assert r.status_code == 200
    assert isinstance(r.json()["summary"], str)
    assert len(r.json()["summary"]) > 0


def test_chat_returns_answer(api_client):
    r = api_client.post("/chat", json={"question": "Which category has the highest revenue?"})
    assert r.status_code == 200
    body = r.json()
    assert body["question"] == "Which category has the highest revenue?"
    assert isinstance(body["answer"], str)


# ── Anomalies ─────────────────────────────────────────────────────────────────

def test_anomalies_returns_list(api_client):
    r = api_client.get("/anomalies")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["anomalies"])
    assert body["count"] > 0


def test_anomalies_with_explain_flag(api_client):
    r = api_client.get("/anomalies?explain=true")
    assert r.status_code == 200
    for item in r.json()["anomalies"]:
        assert item["llm_explanation"] is not None


# ── Data quality ──────────────────────────────────────────────────────────────

def test_data_quality_returns_report(api_client):
    r = api_client.get("/data-quality")
    assert r.status_code == 200
    body = r.json()
    assert "rows_extracted" in body
    assert "rejection_rules" in body


# ── Ingest upload ─────────────────────────────────────────────────────────────

def test_ingest_upload_valid_csv(api_client):
    csv_content = (
        "transaction_id,date,store_id,sku,qty,unit_price,total\n"
        "T9001,2024-06-01,ST1,P1,2,150.0,300.0\n"
        "T9002,2024-06-02,ST2,P2,3,35.0,105.0\n"
    )
    r = api_client.post(
        "/ingest/upload",
        files={"file": ("upload.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rows_extracted"] == 2
    assert body["rows_loaded"] + body["rows_rejected"] == body["rows_extracted"]


def test_ingest_upload_rejects_non_csv(api_client):
    r = api_client.post(
        "/ingest/upload",
        files={"file": ("data.json", io.BytesIO(b"[]"), "application/json")},
    )
    assert r.status_code == 400


def test_ingest_upload_reports_bad_rows(api_client):
    csv_content = (
        "transaction_id,date,store_id,sku,qty,unit_price,total\n"
        "T9901,2024-06-01,,P1,2,150.0,300.0\n"  # null store → rejected
        "T9902,2024-06-01,ST1,P2,3,35.0,105.0\n"
    )
    r = api_client.post(
        "/ingest/upload",
        files={"file": ("upload.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["rows_rejected"] >= 1

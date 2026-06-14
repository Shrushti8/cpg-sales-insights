"""Unit tests for Phase 3 — feature engineering, model, and anomaly detection."""

import numpy as np
import pandas as pd
import pytest

from cpg_insights.db.connection import get_connection
from cpg_insights.forecasting.anomaly import _severity, detect_anomalies
from cpg_insights.forecasting.features import (
    build_monthly_revenue,
    engineer_features,
    make_predict_row,
    to_model_matrix,
)
from cpg_insights.forecasting.model import load_model, predict, train

# ── Feature engineering ───────────────────────────────────────────────────────

def _make_revenue_df(n_months: int = 6) -> pd.DataFrame:
    months = pd.date_range("2024-01-01", periods=n_months, freq="MS").strftime("%Y-%m-%d")
    return pd.DataFrame({
        "month":    list(months) * 2,
        "category": ["Beverages"] * n_months + ["Snacks"] * n_months,
        "region":   ["North"] * n_months + ["South"] * n_months,
        "revenue":  np.arange(1, n_months * 2 + 1, dtype=float) * 100,
        "units":    np.arange(1, n_months * 2 + 1) * 10,
    })


def test_engineer_features_adds_time_columns():
    df = engineer_features(_make_revenue_df())
    for col in ["month_num", "year", "sin_month", "cos_month", "lag_1", "lag_2"]:
        assert col in df.columns


def test_engineer_features_lag1_is_previous_month():
    df = engineer_features(_make_revenue_df(6))
    bev = df[df["category"] == "Beverages"].reset_index(drop=True)
    # lag_1 for row 2 should equal revenue of row 1 (within same group)
    assert bev.loc[2, "lag_1"] == pytest.approx(bev.loc[1, "revenue"])


def test_engineer_features_first_two_rows_per_group_have_nan_lags():
    df = engineer_features(_make_revenue_df(6))
    bev = df[df["category"] == "Beverages"].reset_index(drop=True)
    assert pd.isna(bev.loc[0, "lag_1"])
    assert pd.isna(bev.loc[0, "lag_2"])
    assert pd.isna(bev.loc[1, "lag_2"])


def test_engineer_features_sin_cos_range():
    df = engineer_features(_make_revenue_df(12))
    assert df["sin_month"].between(-1.01, 1.01).all()
    assert df["cos_month"].between(-1.01, 1.01).all()


def test_to_model_matrix_drops_lag_nans():
    df = engineer_features(_make_revenue_df(6)).dropna(subset=["lag_1", "lag_2"])
    X, feature_cols = to_model_matrix(df)
    assert X.isna().sum().sum() == 0


def test_to_model_matrix_creates_dummy_columns():
    df = engineer_features(_make_revenue_df(6)).dropna(subset=["lag_1", "lag_2"])
    X, feature_cols = to_model_matrix(df)
    dummy_cols = [c for c in feature_cols if c.startswith(("category_", "region_"))]
    assert len(dummy_cols) > 0


def test_to_model_matrix_aligns_to_known_dummies():
    df = engineer_features(_make_revenue_df(6)).dropna(subset=["lag_1", "lag_2"])
    _, feature_cols = to_model_matrix(df)
    dummy_cols = [c for c in feature_cols if c.startswith(("category_", "region_"))]

    # Prediction path: unknown category introduces a column not in training
    df2 = df.copy()
    df2["category"] = "NewCat"
    X2, _ = to_model_matrix(df2, dummy_cols=dummy_cols)
    assert list(X2.columns) == feature_cols


def test_make_predict_row_shape(dummy_cols=None):
    if dummy_cols is None:
        dummy_cols = ["category_Snacks", "region_South"]
    row = make_predict_row("Beverages", "North", "2026-01-01", 500.0, 480.0, dummy_cols)
    assert row.shape == (1, 6 + len(dummy_cols))


def test_make_predict_row_sets_correct_dummies():
    dummy_cols = ["category_Snacks", "region_South"]
    row = make_predict_row("Snacks", "South", "2026-01-01", 500.0, 480.0, dummy_cols)
    assert row["category_Snacks"].iloc[0] == 1.0
    assert row["region_South"].iloc[0] == 1.0


def test_make_predict_row_reference_category_zeros():
    dummy_cols = ["category_Snacks", "region_South"]
    # Beverages is the reference (dropped), so its dummy col doesn't exist
    row = make_predict_row("Beverages", "North", "2026-01-01", 500.0, 480.0, dummy_cols)
    assert row["category_Snacks"].iloc[0] == 0.0
    assert row["region_South"].iloc[0] == 0.0


# ── Anomaly detection ─────────────────────────────────────────────────────────

def test_severity_mild():
    assert _severity(2.1) == "mild"
    assert _severity(-2.1) == "mild"


def test_severity_moderate():
    assert _severity(2.6) == "moderate"


def test_severity_severe():
    assert _severity(3.5) == "severe"
    assert _severity(-3.1) == "severe"


class _FakeConn:
    """Minimal DuckDB-like connection for testing anomaly detection offline."""

    def __init__(self, df: pd.DataFrame):
        self._df = df
        self.deleted = False
        self.inserted_rows: list = []

    def execute(self, sql: str, params=None):
        if "DELETE FROM" in sql:
            self.deleted = True
            return self
        if "SELECT" in sql:
            return self
        return self

    def executemany(self, sql: str, rows: list):
        self.inserted_rows.extend(rows)

    def df(self):
        return self._df


def _make_conn_with_spike():
    """Revenue DataFrame with an obvious spike in month 4 for one group."""
    revenues = [100.0] * 12
    revenues[3] = 500.0  # 4σ spike
    df = pd.DataFrame({
        "month":    pd.date_range("2024-01-01", periods=12, freq="MS"),
        "category": ["Beverages"] * 12,
        "region":   ["North"] * 12,
        "revenue":  revenues,
        "units":    [1000] * 12,
    })
    return _FakeConn(df)


def test_detect_anomalies_flags_spike():
    conn = _make_conn_with_spike()
    result = detect_anomalies(conn, z_threshold=2.0)
    assert not result.empty
    assert result["z_score"].abs().max() > 2.0


def test_detect_anomalies_clears_before_insert():
    conn = _make_conn_with_spike()
    detect_anomalies(conn, z_threshold=2.0)
    assert conn.deleted


def test_detect_anomalies_returns_empty_when_no_spikes():
    revenues = list(range(100, 112))  # gentle linear trend, no spike
    df = pd.DataFrame({
        "month":    pd.date_range("2024-01-01", periods=12, freq="MS"),
        "category": ["Beverages"] * 12,
        "region":   ["North"] * 12,
        "revenue":  [float(r) for r in revenues],
        "units":    [1000] * 12,
    })
    conn = _FakeConn(df)
    result = detect_anomalies(conn, z_threshold=3.0)
    assert result.empty


# ── Model end-to-end sanity ───────────────────────────────────────────────────

def test_model_beats_naive_baseline(tmp_path):
    """Ridge model MAE should be better than always predicting the mean."""
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    df = _make_revenue_df(24)
    df = engineer_features(df).dropna(subset=["lag_1", "lag_2"])

    cutoff = sorted(df["month"].unique())[-4]
    train_df = df[df["month"] < cutoff]
    test_df  = df[df["month"] >= cutoff]

    X_train, feature_cols = to_model_matrix(train_df)
    dummy_cols = [c for c in feature_cols if c.startswith(("category_", "region_"))]
    X_test, _ = to_model_matrix(test_df, dummy_cols=dummy_cols)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_s, train_df["revenue"].values)

    y_test  = test_df["revenue"].values
    y_pred  = ridge.predict(X_test_s)
    mae_model = float(np.mean(np.abs(y_test - y_pred)))

    naive_pred = np.full_like(y_test, train_df["revenue"].mean())
    mae_naive  = float(np.mean(np.abs(y_test - naive_pred)))

    assert mae_model < mae_naive, (
        f"Ridge (MAE={mae_model:.1f}) should beat naive mean (MAE={mae_naive:.1f})"
    )


# ── DB-backed model train / predict (real DuckDB) ─────────────────────────────

@pytest.fixture()
def populated_db(tmp_path):
    """A small DuckDB with 2 categories × 2 regions over 10 months of fact_sales."""
    db_path = tmp_path / "test.duckdb"
    conn = get_connection(str(db_path))

    conn.executemany("INSERT INTO dim_product VALUES (?,?,?,?,?,?,?)", [
        ["P1", "Prod1", "CatA", "BrandX", "100ml", 50.0, "2020-01-01"],
        ["P2", "Prod2", "CatB", "BrandY", "100ml", 80.0, "2020-01-01"],
    ])
    conn.executemany("INSERT INTO dim_store VALUES (?,?,?,?,?,?)", [
        ["ST1", "Store1", "RegX", "City1", "State1", "Urban"],
        ["ST2", "Store2", "RegY", "City2", "State2", "Urban"],
    ])

    rows = []
    tid = 0
    for month in range(1, 11):
        d = f"2024-{month:02d}-15"
        for sku, base in [("P1", 50.0), ("P2", 80.0)]:
            for store in ["ST1", "ST2"]:
                for k in range(3):
                    tid += 1
                    qty = 2 + k
                    price = base + month  # mild upward trend so the model has signal
                    rows.append([f"T{tid:05d}", d, store, sku, qty,
                                 price, qty * price, "pos", "store"])
    conn.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?)", rows)
    yield conn, db_path
    conn.close()


def test_build_monthly_revenue_shape(populated_db):
    conn, _ = populated_db
    df = build_monthly_revenue(conn)
    assert set(df["category"]) == {"CatA", "CatB"}
    assert set(df["region"]) == {"RegX", "RegY"}
    assert len(df) == 10 * 2 * 2  # 10 months × 2 categories × 2 regions


def test_train_persists_model_and_metrics(populated_db, tmp_path):
    conn, _ = populated_db
    model_path = tmp_path / "m.pkl"
    metrics = train(conn, holdout_months=2, model_path=model_path)
    assert model_path.exists()
    assert metrics["mae"] >= 0
    assert "mape" in metrics
    n = conn.execute("SELECT COUNT(*) FROM model_metrics").fetchone()[0]
    assert n == 1


def test_load_model_roundtrip(populated_db, tmp_path):
    conn, _ = populated_db
    model_path = tmp_path / "m.pkl"
    train(conn, holdout_months=2, model_path=model_path)
    artifact = load_model(model_path)
    assert {"model", "scaler", "feature_cols", "dummy_cols", "residual_std"} <= artifact.keys()


def test_predict_returns_horizon_rows_with_valid_ci(populated_db, tmp_path):
    conn, _ = populated_db
    model_path = tmp_path / "m.pkl"
    train(conn, holdout_months=2, model_path=model_path)
    result = predict("CatA", "RegX", horizon=3, conn=conn, model_path=model_path)
    assert len(result) == 3
    for r in result:
        assert r["predicted_revenue"] >= 0
        assert r["lower_bound"] <= r["predicted_revenue"] <= r["upper_bound"]


def test_predict_raises_on_insufficient_history(populated_db, tmp_path):
    conn, _ = populated_db
    model_path = tmp_path / "m.pkl"
    train(conn, holdout_months=2, model_path=model_path)
    with pytest.raises(ValueError):
        predict("CatA", "NoSuchRegion", horizon=2, conn=conn, model_path=model_path)


def test_detect_anomalies_persists_to_db(populated_db):
    conn, _ = populated_db
    result = detect_anomalies(conn, z_threshold=0.5)  # low threshold to force flags
    n = conn.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0]
    assert n == len(result)
    assert n > 0

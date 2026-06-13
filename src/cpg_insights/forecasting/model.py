"""
Ridge regression revenue forecasting model.

train()   → fits on historical monthly revenue, evaluates on holdout, persists artifact
predict() → multi-step autoregressive forecast with ±1.96σ confidence interval
"""

import pickle
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler

from cpg_insights.forecasting.features import (
    build_monthly_revenue,
    engineer_features,
    make_predict_row,
    to_model_matrix,
)


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train(
    conn, holdout_months: int = 4, model_path: str | Path = "models/revenue_model.pkl"
) -> dict:
    """
    Train on (total_months - holdout_months), evaluate on the holdout tail.
    Saves a pickle artifact and records metrics in the model_metrics DB table.
    Returns a metrics dict.
    """
    raw = build_monthly_revenue(conn)
    df  = engineer_features(raw)
    df  = df.dropna(subset=["lag_1", "lag_2"]).reset_index(drop=True)

    cutoff = sorted(df["month"].unique())[-holdout_months]
    train_df = df[df["month"] <  cutoff]
    test_df  = df[df["month"] >= cutoff]

    X_train, feature_cols = to_model_matrix(train_df)
    y_train = train_df["revenue"].values

    dummy_cols = [c for c in feature_cols if c.startswith(("category_", "region_"))]

    X_test, _ = to_model_matrix(test_df, dummy_cols=dummy_cols)
    y_test     = test_df["revenue"].values

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_s, y_train)

    y_pred    = ridge.predict(X_test_s)
    residuals = y_test - y_pred
    mae  = float(mean_absolute_error(y_test, y_pred))
    mape = _mape(y_test, y_pred)

    artifact = {
        "model":         ridge,
        "scaler":        scaler,
        "feature_cols":  feature_cols,
        "dummy_cols":    dummy_cols,
        "residual_std":  float(np.std(residuals)),
        "metrics":       {"mae": mae, "mape": mape},
        "trained_at":    datetime.now(UTC).isoformat(),
    }

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as fh:
        pickle.dump(artifact, fh)

    conn.execute("""
        INSERT INTO model_metrics (run_id, trained_at, mae, mape, holdout_months, n_train, n_test)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [str(uuid.uuid4()), datetime.now(UTC), mae, mape,
          holdout_months, len(train_df), len(test_df)])

    return {
        "mae":           round(mae, 2),
        "mape":          round(mape, 2),
        "n_train":       len(train_df),
        "n_test":        len(test_df),
        "holdout_months": holdout_months,
    }


def load_model(model_path: str | Path) -> dict:
    with open(model_path, "rb") as fh:
        return pickle.load(fh)


def predict(
    category: str,
    region: str,
    horizon: int,
    conn,
    model_path: str | Path = "models/revenue_model.pkl",
) -> list[dict]:
    """
    Forecast `horizon` months ahead for a given category × region.
    Returns list of {month, predicted_revenue, lower_bound, upper_bound}.
    """
    artifact = load_model(model_path)
    ridge:       Ridge          = artifact["model"]
    scaler:      StandardScaler = artifact["scaler"]
    dummy_cols:  list[str]      = artifact["dummy_cols"]
    residual_std: float         = artifact["residual_std"]
    ci_half = 1.96 * residual_std

    # Seed lags from the most recent 2 actuals for this category × region
    history = conn.execute("""
        SELECT DATE_TRUNC('month', f.txn_date)::DATE AS month,
               SUM(f.total_amount) AS revenue
        FROM fact_sales f
        JOIN dim_product p ON f.sku_id = p.sku_id
        JOIN dim_store   s ON f.store_id = s.store_id
        WHERE p.category = ? AND s.region = ?
        GROUP BY 1 ORDER BY 1 DESC LIMIT 2
    """, [category, region]).df()

    if len(history) < 2:
        raise ValueError(f"Not enough history for {category}/{region} to seed lag features")

    revenues = history["revenue"].tolist()  # [most_recent, one_before]
    lag_1, lag_2 = revenues[0], revenues[1]

    last_month = pd.Timestamp(history["month"].iloc[0])
    results = []

    for step in range(1, horizon + 1):
        next_month = last_month + pd.DateOffset(months=step)
        month_str  = next_month.strftime("%Y-%m-%d")

        row = make_predict_row(category, region, month_str, lag_1, lag_2, dummy_cols)
        X_s = scaler.transform(row)
        pred = float(ridge.predict(X_s)[0])
        pred = max(pred, 0.0)  # revenue can't be negative

        results.append({
            "month":             month_str,
            "predicted_revenue": round(pred, 2),
            "lower_bound":       round(max(pred - ci_half, 0.0), 2),
            "upper_bound":       round(pred + ci_half, 2),
        })

        lag_2, lag_1 = lag_1, pred  # roll lags forward for next step

    return results

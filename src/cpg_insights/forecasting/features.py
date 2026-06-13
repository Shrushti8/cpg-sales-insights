"""Feature engineering for the CPG revenue forecasting model."""

import numpy as np
import pandas as pd

NUMERIC_FEATURES = ["year", "month_num", "sin_month", "cos_month", "lag_1", "lag_2"]


def build_monthly_revenue(conn) -> pd.DataFrame:
    """Aggregate fact_sales to monthly revenue by category × region."""
    return conn.execute("""
        SELECT
            DATE_TRUNC('month', f.txn_date)::DATE  AS month,
            p.category,
            s.region,
            SUM(f.total_amount)                    AS revenue,
            SUM(f.quantity)                        AS units
        FROM fact_sales f
        JOIN dim_product p ON f.sku_id = p.sku_id
        JOIN dim_store   s ON f.store_id = s.store_id
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """).df()


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time, seasonality, and lag features to a monthly revenue DataFrame."""
    df = df.copy()
    month_dt = pd.to_datetime(df["month"])
    df["month_num"] = month_dt.dt.month
    df["year"]      = month_dt.dt.year
    df["sin_month"] = np.sin(2 * np.pi * df["month_num"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["month_num"] / 12)

    df = df.sort_values(["category", "region", "month"]).reset_index(drop=True)
    df["lag_1"] = df.groupby(["category", "region"])["revenue"].shift(1)
    df["lag_2"] = df.groupby(["category", "region"])["revenue"].shift(2)
    return df


def to_model_matrix(
    df: pd.DataFrame,
    dummy_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    One-hot encode category + region, align to dummy_cols if provided (prediction path).
    Returns (X DataFrame, feature_cols list).
    """
    encoded = pd.get_dummies(df, columns=["category", "region"], drop_first=True, dtype=float)
    new_dummy_cols = [c for c in encoded.columns if c.startswith(("category_", "region_"))]

    if dummy_cols is not None:
        for col in dummy_cols:
            if col not in encoded.columns:
                encoded[col] = 0.0
        use_dummies = dummy_cols
    else:
        use_dummies = new_dummy_cols

    feature_cols = NUMERIC_FEATURES + use_dummies
    return encoded[feature_cols].copy(), feature_cols


def make_predict_row(
    category: str,
    region: str,
    month: str,
    lag_1: float,
    lag_2: float,
    dummy_cols: list[str],
) -> pd.DataFrame:
    """Build a single-row feature DataFrame for one forecast step."""
    month_dt = pd.Timestamp(month)
    row: dict = {
        "year":      float(month_dt.year),
        "month_num": float(month_dt.month),
        "sin_month": float(np.sin(2 * np.pi * month_dt.month / 12)),
        "cos_month": float(np.cos(2 * np.pi * month_dt.month / 12)),
        "lag_1":     lag_1,
        "lag_2":     lag_2,
    }
    for col in dummy_cols:
        row[col] = 0.0
    cat_col = f"category_{category}"
    reg_col = f"region_{region}"
    if cat_col in row:
        row[cat_col] = 1.0
    if reg_col in row:
        row[reg_col] = 1.0

    feature_cols = NUMERIC_FEATURES + dummy_cols
    return pd.DataFrame([row])[feature_cols]

"""
Z-score anomaly detection on monthly revenue per category × region.

Flags months where revenue deviates more than z_threshold standard deviations
from the group mean. Results are persisted to the `anomalies` DuckDB table.
"""

import uuid
from datetime import UTC, datetime

import pandas as pd

from cpg_insights.forecasting.features import build_monthly_revenue


def _severity(z: float) -> str:
    az = abs(z)
    if az >= 3.0:
        return "severe"
    if az >= 2.5:
        return "moderate"
    return "mild"


def _description(row: pd.Series) -> str:
    direction = "above" if row["z_score"] > 0 else "below"
    pct = abs((row["actual_revenue"] - row["group_mean"]) / row["group_mean"] * 100)
    m = row["month"]
    month_label = m.strftime("%b %Y") if hasattr(m, "strftime") else str(m)[:7]
    return (
        f"{row['category']} revenue in {row['region']} for {month_label} "
        f"was {pct:.1f}% {direction} the group mean "
        f"(z-score: {row['z_score']:+.2f})"
    )


def detect_anomalies(conn, z_threshold: float = 2.0) -> pd.DataFrame:
    """
    Compute z-scores over the 24-month history per category × region.
    Clears previous anomalies and writes fresh results to the anomalies table.
    Returns the flagged DataFrame (may be empty).
    """
    df = build_monthly_revenue(conn)
    df["month"] = pd.to_datetime(df["month"])

    stats = df.groupby(["category", "region"])["revenue"].agg(
        group_mean="mean", group_std="std"
    ).reset_index()
    df = df.merge(stats, on=["category", "region"])

    df["z_score"] = (df["revenue"] - df["group_mean"]) / df["group_std"].replace(0, 1)
    flagged = df[df["z_score"].abs() >= z_threshold].copy()
    flagged = flagged.rename(columns={"revenue": "actual_revenue"})

    conn.execute("DELETE FROM anomalies")

    if flagged.empty:
        return flagged

    flagged["severity"]    = flagged["z_score"].apply(_severity)
    flagged["description"] = flagged.apply(_description, axis=1)
    now = datetime.now(UTC)

    rows = [
        (
            str(uuid.uuid4()),
            now,
            row["month"].date(),
            row["category"],
            row["region"],
            round(row["actual_revenue"], 2),
            round(row["z_score"], 4),
            row["severity"],
            row["description"],
        )
        for _, row in flagged.iterrows()
    ]

    conn.executemany("""
        INSERT INTO anomalies
            (anomaly_id, detected_at, month, category, region,
             actual_revenue, z_score, severity, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    return flagged[
        ["month", "category", "region", "actual_revenue", "z_score", "severity", "description"]
    ].reset_index(drop=True)

"""
Load stage — writes clean data into the DuckDB star schema.

Tables written:
  dim_product           — product catalogue (upsert)
  dim_store             — store/region reference (upsert)
  dim_date              — date dimension derived from fact dates (upsert)
  fact_sales            — clean unified transactions (insert, skip duplicates)
  pipeline_runs         — one row per pipeline run with quality report
  rejected_transactions — quarantine table; full raw row stored as JSON for review
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from cpg_insights.pipeline.validate import QualityReport


def load_dimensions(conn: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    products = pd.read_csv(raw_dir / "product_master.csv")
    conn.execute("DELETE FROM dim_product")
    conn.executemany(
        """INSERT OR REPLACE INTO dim_product
           VALUES (?,?,?,?,?,?,?)""",
        products[["sku_id","name","category","brand","package_size","list_price","launch_date"]].values.tolist(),
    )

    stores = pd.read_csv(raw_dir / "store_regions.csv")
    conn.execute("DELETE FROM dim_store")
    conn.executemany(
        """INSERT OR REPLACE INTO dim_store
           VALUES (?,?,?,?,?,?)""",
        stores[["store_id","store_name","region","city","state","segment"]].values.tolist(),
    )


def _build_date_dim(dates: pd.Series) -> pd.DataFrame:
    unique_dates = pd.to_datetime(dates.dropna().unique())
    rows = []
    for d in unique_dates:
        rows.append({
            "date_id": d.date(),
            "year": d.year,
            "quarter": d.quarter,
            "month": d.month,
            "month_name": d.strftime("%B"),
            "week": int(d.strftime("%W")),
            "day_of_week": d.dayofweek,
        })
    return pd.DataFrame(rows)


def load_facts(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    # Build and load date dimension
    date_dim = _build_date_dim(df["txn_date"])
    if not date_dim.empty:
        conn.executemany(
            "INSERT OR REPLACE INTO dim_date VALUES (?,?,?,?,?,?,?)",
            date_dim.values.tolist(),
        )

    # Load fact_sales — skip rows with duplicate transaction_id already in DB
    existing = set(
        r[0] for r in conn.execute("SELECT transaction_id FROM fact_sales").fetchall()
    )
    new_rows = df[~df["transaction_id"].isin(existing)]

    cols = ["transaction_id","txn_date","store_id","sku_id",
            "quantity","unit_price","total_amount","source","channel"]
    rows = new_rows[cols].values.tolist()
    if rows:
        conn.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?)", rows)

    return len(rows)


def load_rejected(conn: duckdb.DuckDBPyConnection, rejected_df: pd.DataFrame) -> int:
    """Write rejected rows to the quarantine table with their rejection reason."""
    if rejected_df.empty:
        return 0

    rows = []
    for _, row in rejected_df.iterrows():
        raw = row.drop("rejection_reason", errors="ignore").to_dict()
        rows.append([
            str(uuid.uuid4()),
            raw.get("transaction_id"),
            raw.get("source"),
            row.get("rejection_reason", "unknown"),
            json.dumps(raw, default=str),
            datetime.utcnow(),
        ])

    conn.executemany(
        "INSERT INTO rejected_transactions VALUES (?,?,?,?,?,?)", rows
    )
    return len(rows)


def save_quality_report(
    conn: duckdb.DuckDBPyConnection,
    report: QualityReport,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO pipeline_runs VALUES (?,?,?,?,?,?,?)",
        [
            str(uuid.uuid4()),
            datetime.utcnow(),
            report.source,
            report.rows_extracted,
            report.rows_valid,
            report.rows_rejected,
            json.dumps(report.rejection_rules),
        ],
    )

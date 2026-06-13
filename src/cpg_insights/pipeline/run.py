"""
Pipeline entry point — orchestrates all five stages.

Usage:
    python -m cpg_insights.pipeline.run
    make pipeline
"""

from pathlib import Path

import pandas as pd

from cpg_insights.db.connection import get_connection
from cpg_insights.pipeline.dedupe import dedupe
from cpg_insights.pipeline.extract import extract_all
from cpg_insights.pipeline.load import (
    load_dimensions,
    load_facts,
    load_rejected,
    save_quality_report,
)
from cpg_insights.pipeline.transform import transform
from cpg_insights.pipeline.validate import validate

RAW_DIR = Path("data/raw")


def run_pipeline(raw_dir: Path = RAW_DIR, db_path: str | None = None) -> dict:
    """
    Run the full ingestion pipeline. Returns a summary dict.
    """
    conn = get_connection(db_path)

    # ── 1. Extract ────────────────────────────────────────────────────────────
    print("Stage 1/5 — Extract")
    df = extract_all(raw_dir)
    print(f"  {len(df):,} rows extracted from {raw_dir}")

    # ── 2. Validate ───────────────────────────────────────────────────────────
    print("Stage 2/5 — Validate")
    valid_skus = set(
        pd.read_csv(raw_dir / "product_master.csv")["sku_id"].tolist()
    )
    clean_df, rejected_df, report = validate(df, valid_skus, source_name="combined")
    print(report.summary())

    # ── 3. Transform ──────────────────────────────────────────────────────────
    print("Stage 3/5 — Transform")
    clean_df = transform(clean_df)
    print("  Dates normalised, prices cleaned, types cast")

    # ── 4. Dedupe ─────────────────────────────────────────────────────────────
    print("Stage 4/5 — Dedupe")
    clean_df, n_dupes = dedupe(clean_df)
    print(f"  {n_dupes:,} duplicate transaction IDs removed")

    # ── 5. Load ───────────────────────────────────────────────────────────────
    print("Stage 5/5 — Load")
    load_dimensions(conn, raw_dir)
    n_inserted = load_facts(conn, clean_df)
    n_quarantined = load_rejected(conn, rejected_df)
    save_quality_report(conn, report)
    conn.close()
    print(f"  {n_inserted:,} rows inserted into fact_sales")
    print(f"  {n_quarantined:,} rows written to rejected_transactions (quarantine)")

    summary = {
        "rows_extracted": report.rows_extracted,
        "rows_valid": report.rows_valid,
        "rows_rejected": report.rows_rejected,
        "duplicates_removed": n_dupes,
        "rows_loaded": n_inserted,
        "rows_quarantined": n_quarantined,
        "rejection_rules": report.rejection_rules,
    }
    print("\nPipeline complete.", summary)
    return summary


if __name__ == "__main__":
    run_pipeline()

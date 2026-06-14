"""GET /data-quality — latest pipeline run quality report."""

import json

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from cpg_insights.api.deps import get_conn
from cpg_insights.api.schemas import DataQualityResponse

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("", response_model=DataQualityResponse)
def data_quality(conn: duckdb.DuckDBPyConnection = Depends(get_conn)):
    row = conn.execute("""
        SELECT rows_extracted, rows_valid, rows_rejected, rejection_rules
        FROM pipeline_runs ORDER BY run_at DESC LIMIT 1
    """).fetchone()

    if not row:
        raise HTTPException(
            status_code=404, detail="No pipeline runs found. Run the pipeline first."
        )

    return DataQualityResponse(
        rows_extracted=row[0],
        rows_valid=row[1],
        rows_rejected=row[2],
        rejection_rules=json.loads(row[3]),
    )

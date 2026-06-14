"""GET /anomalies — detected revenue anomalies with optional LLM explanations."""

import duckdb
from fastapi import APIRouter, Depends, Query

from cpg_insights.api.deps import get_conn, get_llm
from cpg_insights.api.schemas import AnomaliesResponse, AnomalyItem
from cpg_insights.llm.base import LLMProvider
from cpg_insights.llm.insights import explain_anomaly

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get("", response_model=AnomaliesResponse)
def get_anomalies(
    explain: bool = Query(False, description="Attach LLM explanation to each anomaly"),
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
    llm: LLMProvider = Depends(get_llm),
):
    rows = conn.execute("""
        SELECT month, category, region, actual_revenue, z_score, severity, description
        FROM anomalies ORDER BY ABS(z_score) DESC
    """).fetchall()

    items = []
    for r in rows:
        month, category, region, actual_revenue, z_score, severity, description = r
        llm_explanation = None
        if explain:
            llm_explanation = explain_anomaly(
                str(month), category, region, actual_revenue, z_score, severity, llm
            )
        items.append(AnomalyItem(
            month=str(month), category=category, region=region,
            actual_revenue=actual_revenue, z_score=z_score,
            severity=severity, description=description,
            llm_explanation=llm_explanation,
        ))

    return AnomaliesResponse(count=len(items), anomalies=items)

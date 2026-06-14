"""POST /forecast and POST /forecast/explain."""

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from cpg_insights.api.deps import get_conn, get_llm
from cpg_insights.api.schemas import (
    ForecastExplainResponse,
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
)
from cpg_insights.config import settings
from cpg_insights.forecasting.model import predict
from cpg_insights.llm.base import LLMProvider
from cpg_insights.llm.insights import explain_forecast

router = APIRouter(prefix="/forecast", tags=["Forecast"])


def _run_forecast(req: ForecastRequest, conn: duckdb.DuckDBPyConnection) -> list[ForecastPoint]:
    try:
        rows = predict(req.category, req.region, req.horizon, conn, settings.model_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. Run `make train` first.",
        )
    return [ForecastPoint(**r) for r in rows]


@router.post("", response_model=ForecastResponse)
def forecast(req: ForecastRequest, conn: duckdb.DuckDBPyConnection = Depends(get_conn)):
    points = _run_forecast(req, conn)
    return ForecastResponse(category=req.category, region=req.region, forecast=points)


@router.post("/explain", response_model=ForecastExplainResponse)
def forecast_explain(
    req: ForecastRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
    llm: LLMProvider = Depends(get_llm),
):
    points = _run_forecast(req, conn)
    forecast_data = [p.model_dump() for p in points]
    explanation = explain_forecast(req.category, req.region, forecast_data, conn, llm)
    return ForecastExplainResponse(
        category=req.category, region=req.region, forecast=points, explanation=explanation
    )

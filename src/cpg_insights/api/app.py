"""FastAPI application — all routers registered here."""

from datetime import UTC, datetime

from fastapi import FastAPI

from cpg_insights.api.routers import anomalies, data_quality, forecast, ingest, insights, metrics

app = FastAPI(
    title="CPG Sales Insights API",
    description=(
        "Revenue forecasting + LLM insights for CPG sales data. "
        "Interactive docs at /docs — try the endpoints live."
    ),
    version="0.1.0",
)

app.include_router(metrics.router)
app.include_router(forecast.router)
app.include_router(insights.router)
app.include_router(anomalies.router)
app.include_router(data_quality.router)
app.include_router(ingest.router)


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

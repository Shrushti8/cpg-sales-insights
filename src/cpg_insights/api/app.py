"""FastAPI application — Phase 5 will add all routers."""

from datetime import UTC, datetime

from fastapi import FastAPI

app = FastAPI(
    title="CPG Sales Insights API",
    description="Revenue forecasting + LLM insights for CPG sales data.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel, Field

# ── Forecast ──────────────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    category: str = Field(..., examples=["Beverages"])
    region: str = Field(..., examples=["North"])
    horizon: int = Field(3, ge=1, le=12, description="Months ahead to forecast")


class ForecastPoint(BaseModel):
    month: str
    predicted_revenue: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    category: str
    region: str
    forecast: list[ForecastPoint]


class ForecastExplainResponse(BaseModel):
    category: str
    region: str
    forecast: list[ForecastPoint]
    explanation: str


# ── Metrics ───────────────────────────────────────────────────────────────────

class CategoryRevenue(BaseModel):
    category: str
    revenue: float
    units: int


class RegionRevenue(BaseModel):
    region: str
    revenue: float
    units: int


class TopSku(BaseModel):
    name: str
    category: str
    revenue: float


class MetricsSummaryResponse(BaseModel):
    by_category: list[CategoryRevenue]
    by_region: list[RegionRevenue]
    top_skus: list[TopSku]


# ── Insights / Chat ───────────────────────────────────────────────────────────

class InsightsSummaryResponse(BaseModel):
    summary: str


class ChatRequest(BaseModel):
    question: str = Field(..., examples=["Which category has the highest revenue?"])


class ChatResponse(BaseModel):
    question: str
    answer: str


# ── Anomalies ─────────────────────────────────────────────────────────────────

class AnomalyItem(BaseModel):
    month: str
    category: str
    region: str
    actual_revenue: float
    z_score: float
    severity: str
    description: str
    llm_explanation: str | None = None


class AnomaliesResponse(BaseModel):
    count: int
    anomalies: list[AnomalyItem]


# ── Data quality ──────────────────────────────────────────────────────────────

class DataQualityResponse(BaseModel):
    rows_extracted: int
    rows_valid: int
    rows_rejected: int
    rejection_rules: dict[str, int]


# ── Ingest upload ─────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    rows_extracted: int
    rows_valid: int
    rows_rejected: int
    rows_loaded: int
    rejection_rules: dict[str, int]

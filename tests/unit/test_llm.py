"""Unit tests for Phase 4 — LLM provider interface and insights service."""

import pytest

from cpg_insights.llm import get_provider
from cpg_insights.llm.base import LLMProvider
from cpg_insights.llm.insights import (
    _resolve_queries,
    answer_question,
    explain_anomaly,
    explain_forecast,
    get_summary,
)
from cpg_insights.llm.mock import MockProvider

# ── Provider interface ────────────────────────────────────────────────────────

def test_mock_provider_is_llm_provider():
    assert isinstance(MockProvider(), LLMProvider)


def test_mock_provider_returns_string():
    result = MockProvider().generate("What is the revenue trend?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_mock_provider_forecast_response():
    result = MockProvider().generate("explain this forecast for Beverages")
    assert "forecast" in result.lower() or "trend" in result.lower()


def test_mock_provider_anomaly_response():
    result = MockProvider().generate("there is an anomaly spike in sales")
    assert isinstance(result, str)
    assert len(result) > 0


def test_mock_provider_summary_response():
    result = MockProvider().generate("give me an overview summary of trends")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_provider_returns_mock_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    provider = get_provider()
    assert isinstance(provider, MockProvider)


def test_get_provider_gemini_raises_without_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    # Re-import settings so env vars take effect
    import importlib

    import cpg_insights.config as cfg_mod
    cfg_mod.settings.__dict__["llm_provider"] = "gemini"
    cfg_mod.settings.__dict__["gemini_api_key"] = ""
    import cpg_insights.llm as llm_mod
    importlib.reload(llm_mod)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        llm_mod.get_provider()
    # Restore
    cfg_mod.settings.__dict__["llm_provider"] = "mock"
    cfg_mod.settings.__dict__["gemini_api_key"] = ""
    importlib.reload(llm_mod)


# ── Intent resolution ─────────────────────────────────────────────────────────

def test_resolve_queries_anomaly_keywords():
    queries = _resolve_queries("Are there any anomalies this month?")
    assert "anomalies" in queries


def test_resolve_queries_category_keyword():
    queries = _resolve_queries("Which category has the highest revenue?")
    assert "revenue_by_category" in queries


def test_resolve_queries_region_keyword():
    queries = _resolve_queries("How is the North region doing?")
    assert "revenue_by_region" in queries


def test_resolve_queries_trend_keyword():
    queries = _resolve_queries("Show me the monthly trend over time")
    assert "monthly_trend" in queries


def test_resolve_queries_top_sku_keyword():
    queries = _resolve_queries("What are the top products?")
    assert "top_skus" in queries


def test_resolve_queries_quality_keyword():
    queries = _resolve_queries("How many rows were rejected in the pipeline?")
    assert "pipeline_quality" in queries


def test_resolve_queries_default_fallback():
    queries = _resolve_queries("Tell me something interesting")
    assert len(queries) > 0  # falls back to defaults


# ── Insights service with mock DB ─────────────────────────────────────────────

class _FakeConn:
    """Minimal DuckDB-like connection returning empty result sets."""

    def execute(self, sql: str, params=None):
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return None


def test_get_summary_returns_string():
    result = get_summary(_FakeConn(), MockProvider())
    assert isinstance(result, str)
    assert len(result) > 0


def test_answer_question_returns_string():
    result = answer_question("What is the revenue by category?", _FakeConn(), MockProvider())
    assert isinstance(result, str)
    assert len(result) > 0


def test_explain_forecast_returns_string():
    forecast = [{"month": "2026-01-01", "predicted_revenue": 50000.0,
                 "lower_bound": 45000.0, "upper_bound": 55000.0}]
    result = explain_forecast("Beverages", "North", forecast, _FakeConn(), MockProvider())
    assert isinstance(result, str)
    assert len(result) > 0


def test_explain_anomaly_returns_string():
    result = explain_anomaly(
        month="2024-07",
        category="Beverages",
        region="North",
        actual_revenue=95000.0,
        z_score=3.2,
        severity="severe",
        llm=MockProvider(),
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_explain_anomaly_dip_direction():
    result = explain_anomaly(
        month="2024-02",
        category="Snacks",
        region="South",
        actual_revenue=12000.0,
        z_score=-2.4,
        severity="moderate",
        llm=MockProvider(),
    )
    assert isinstance(result, str)

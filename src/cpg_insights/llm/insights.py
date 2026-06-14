"""
LLM insights service.

Design: the LLM never sees raw SQL and never executes queries.
  1. A fixed menu of parameterized queries runs against DuckDB.
  2. Their results (plain Python dicts/lists) are serialised into the prompt.
  3. The LLM turns the data into prose.

This keeps the chat safe by construction — no prompt injection can cause
arbitrary DB writes or reads beyond the whitelisted set.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from cpg_insights.llm.base import LLMProvider

# ── Whitelisted query registry ─────────────────────────────────────────────────

def _q_revenue_by_category(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = conn.execute("""
        SELECT dp.category,
               SUM(fs.total_amount) AS revenue,
               SUM(fs.quantity)     AS units
        FROM   fact_sales fs
        JOIN   dim_product dp ON fs.sku_id = dp.sku_id
        GROUP  BY dp.category
        ORDER  BY revenue DESC
    """).fetchall()
    cols = ["category", "revenue", "units"]
    return [dict(zip(cols, r)) for r in rows]


def _q_revenue_by_region(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = conn.execute("""
        SELECT ds.region,
               SUM(fs.total_amount) AS revenue,
               SUM(fs.quantity)     AS units
        FROM   fact_sales fs
        JOIN   dim_store ds ON fs.store_id = ds.store_id
        GROUP  BY ds.region
        ORDER  BY revenue DESC
    """).fetchall()
    cols = ["region", "revenue", "units"]
    return [dict(zip(cols, r)) for r in rows]


def _q_monthly_trend(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = conn.execute("""
        SELECT strftime(fs.txn_date, '%Y-%m') AS month,
               SUM(fs.total_amount)           AS revenue
        FROM   fact_sales fs
        GROUP  BY month
        ORDER  BY month
    """).fetchall()
    cols = ["month", "revenue"]
    return [dict(zip(cols, r)) for r in rows]


def _q_top_skus(conn: duckdb.DuckDBPyConnection, n: int = 5) -> list[dict]:
    rows = conn.execute("""
        SELECT dp.name, dp.category, SUM(fs.total_amount) AS revenue
        FROM   fact_sales fs
        JOIN   dim_product dp ON fs.sku_id = dp.sku_id
        GROUP  BY dp.name, dp.category
        ORDER  BY revenue DESC
        LIMIT  ?
    """, [n]).fetchall()
    cols = ["name", "category", "revenue"]
    return [dict(zip(cols, r)) for r in rows]


def _q_anomalies(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = conn.execute("""
        SELECT month, category, region, actual_revenue, z_score, severity, description
        FROM   anomalies
        ORDER  BY ABS(z_score) DESC
        LIMIT  10
    """).fetchall()
    cols = ["month", "category", "region", "actual_revenue", "z_score", "severity", "description"]
    return [dict(zip(cols, r)) for r in rows]


def _q_pipeline_quality(conn: duckdb.DuckDBPyConnection) -> dict:
    row = conn.execute("""
        SELECT rows_extracted, rows_valid, rows_rejected
        FROM   pipeline_runs
        ORDER  BY run_at DESC
        LIMIT  1
    """).fetchone()
    if not row:
        return {}
    return {"rows_extracted": row[0], "rows_valid": row[1], "rows_rejected": row[2]}


# Maps a user-facing intent keyword → query function
QUERY_REGISTRY: dict[str, callable] = {
    "revenue_by_category": _q_revenue_by_category,
    "revenue_by_region": _q_revenue_by_region,
    "monthly_trend": _q_monthly_trend,
    "top_skus": _q_top_skus,
    "anomalies": _q_anomalies,
    "pipeline_quality": _q_pipeline_quality,
}

# Keywords in user question → which queries to run
_INTENT_MAP: list[tuple[list[str], list[str]]] = [
    (["anomal", "spike", "unusual", "outlier"],  ["anomalies", "monthly_trend"]),
    (["category", "categor"],                    ["revenue_by_category"]),
    (["region", "area", "zone", "north", "south", "east", "west", "central"],
                                                 ["revenue_by_region"]),
    (["trend", "month", "over time", "growth"],  ["monthly_trend"]),
    (["top", "best", "leading", "product", "sku"],["top_skus", "revenue_by_category"]),
    (["quality", "reject", "pipeline", "clean"], ["pipeline_quality"]),
]
_DEFAULT_QUERIES = ["revenue_by_category", "revenue_by_region", "monthly_trend"]


def _resolve_queries(question: str) -> list[str]:
    lower = question.lower()
    selected: list[str] = []
    for keywords, queries in _INTENT_MAP:
        if any(kw in lower for kw in keywords):
            for q in queries:
                if q not in selected:
                    selected.append(q)
    return selected or _DEFAULT_QUERIES


# ── Public API ─────────────────────────────────────────────────────────────────

def get_summary(conn: duckdb.DuckDBPyConnection, llm: LLMProvider) -> str:
    """Return an NL summary of overall sales performance."""
    data = {
        "revenue_by_category": _q_revenue_by_category(conn),
        "revenue_by_region": _q_revenue_by_region(conn),
        "monthly_trend": _q_monthly_trend(conn),
        "top_skus": _q_top_skus(conn),
        "anomalies": _q_anomalies(conn),
    }
    prompt = (
        "You are a CPG (consumer packaged goods) sales analyst for an Indian market company. "
        "All revenue values are in Indian Rupees. Always use the ₹ symbol for every amount. "
        "Write a concise 3–5 sentence executive summary of the following sales data. "
        "Highlight the top-performing category, strongest region, any notable trends, "
        "and whether anomalies need attention. Use plain business language, no jargon.\n\n"
        f"Sales data:\n{json.dumps(data, default=str, indent=2)}"
    )
    return llm.generate(prompt)


def answer_question(
    question: str,
    conn: duckdb.DuckDBPyConnection,
    llm: LLMProvider,
) -> str:
    """Answer a natural-language question about sales using whitelisted queries."""
    query_keys = _resolve_queries(question)
    data: dict[str, object] = {}
    for key in query_keys:
        fn = QUERY_REGISTRY[key]
        data[key] = fn(conn)

    prompt = (
        "You are a CPG sales analyst assistant for an Indian market company. "
        "All revenue values are in Indian Rupees. Always use the ₹ symbol for every amount. "
        "Answer the following question using ONLY the data provided below. "
        "Be concise (2–4 sentences). If the data does not contain enough information "
        "to answer, say so clearly.\n\n"
        f"Question: {question}\n\n"
        f"Data:\n{json.dumps(data, default=str, indent=2)}"
    )
    return llm.generate(prompt)


def explain_forecast(
    category: str,
    region: str,
    forecast_rows: list[dict],
    conn: duckdb.DuckDBPyConnection,
    llm: LLMProvider,
) -> str:
    """Return a plain-English explanation of a forecast and its drivers."""
    trend = _q_monthly_trend(conn)
    cat_data = [r for r in _q_revenue_by_category(conn) if r["category"] == category]
    prompt = (
        "You are a CPG sales analyst for an Indian market company. "
        "All revenue values are in Indian Rupees. Always use the ₹ symbol for every amount. "
        "Explain the following revenue forecast in plain English for a non-technical business audience. "
        "Cover: (1) what the trend looks like, (2) likely seasonal or demand drivers, "
        "(3) confidence in the projection. Keep it to 3–5 sentences.\n\n"
        f"Category: {category}\nRegion: {region}\n"
        f"Forecast (next months): {json.dumps(forecast_rows, default=str)}\n"
        f"Historical monthly trend: {json.dumps(trend[-12:], default=str)}\n"
        f"Category totals: {json.dumps(cat_data, default=str)}"
    )
    return llm.generate(prompt)


def explain_anomaly(
    month: str,
    category: str,
    region: str,
    actual_revenue: float,
    z_score: float,
    severity: str,
    llm: LLMProvider,
) -> str:
    """Return a one-line business explanation for a detected anomaly."""
    direction = "spike" if z_score > 0 else "dip"
    prompt = (
        f"In one sentence, suggest the most likely business reason for a revenue {direction} "
        f"({severity} severity, z-score {z_score:.1f}) in the {category} category, "
        f"{region} region of India, during {month}. "
        "All amounts are in Indian Rupees (₹). "
        "Keep it factual and brief — no hedging phrases like 'it could be'."
    )
    return llm.generate(prompt)

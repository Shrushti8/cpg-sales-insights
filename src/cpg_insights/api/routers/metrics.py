"""GET /metrics/summary — revenue aggregates by category, region, and top SKUs."""

import duckdb
from fastapi import APIRouter, Depends

from cpg_insights.api.deps import get_conn
from cpg_insights.api.schemas import CategoryRevenue, MetricsSummaryResponse, RegionRevenue, TopSku

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
def metrics_summary(conn: duckdb.DuckDBPyConnection = Depends(get_conn)):
    by_cat = conn.execute("""
        SELECT dp.category, SUM(fs.total_amount) AS revenue, SUM(fs.quantity) AS units
        FROM fact_sales fs JOIN dim_product dp ON fs.sku_id = dp.sku_id
        GROUP BY dp.category ORDER BY revenue DESC
    """).fetchall()

    by_reg = conn.execute("""
        SELECT ds.region, SUM(fs.total_amount) AS revenue, SUM(fs.quantity) AS units
        FROM fact_sales fs JOIN dim_store ds ON fs.store_id = ds.store_id
        GROUP BY ds.region ORDER BY revenue DESC
    """).fetchall()

    top = conn.execute("""
        SELECT dp.name, dp.category, SUM(fs.total_amount) AS revenue
        FROM fact_sales fs JOIN dim_product dp ON fs.sku_id = dp.sku_id
        GROUP BY dp.name, dp.category ORDER BY revenue DESC LIMIT 5
    """).fetchall()

    return MetricsSummaryResponse(
        by_category=[CategoryRevenue(category=r[0], revenue=r[1], units=r[2]) for r in by_cat],
        by_region=[RegionRevenue(region=r[0], revenue=r[1], units=r[2]) for r in by_reg],
        top_skus=[TopSku(name=r[0], category=r[1], revenue=r[2]) for r in top],
    )

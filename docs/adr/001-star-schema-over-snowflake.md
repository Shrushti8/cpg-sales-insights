# ADR 001 — Star Schema over Snowflake Schema

**Status:** Accepted  
**Date:** 2026-06-13

## Context

We needed to choose a schema design for the DuckDB analytical store that holds CPG sales data. The two standard options for dimensional modelling are:

- **Star schema** — flat dimension tables joined directly to the fact table
- **Snowflake schema** — dimension tables further normalised into sub-dimensions (e.g. `dim_store` → `dim_region` → `dim_country`)

## Decision

We chose **star schema**.

## Reasons

**1. Query simplicity.**  
Dashboard and API queries are of the form "total revenue by region and category per month." In a star schema that is one join per dimension. In a snowflake schema, getting region requires joining `fact_sales → dim_store → dim_region` — two joins instead of one, for every query. At the scale of this skeleton (50k rows), the difference is negligible in runtime, but the added SQL complexity gives no benefit.

**2. DuckDB is an analytics engine, not a transactional database.**  
DuckDB uses columnar storage and vectorised execution — it is built specifically for the read-heavy analytical queries a dashboard runs. The normalisation benefit of snowflake (avoiding update anomalies) matters in OLTP systems where rows are updated in place. In our append-only fact table, that concern does not apply.

**3. Dimensions are small and slow-changing.**  
Product master (36 SKUs) and store list (25 stores) change rarely. Storing `region` directly on `dim_store` does not introduce meaningful redundancy. If the dimension grew to millions of rows with frequent updates, revisiting normalisation would make sense.

**4. Skeleton readability.**  
The project team inheriting this skeleton should be able to understand the schema at a glance. Star schema is immediately readable; snowflake requires tracing multiple join paths before the structure becomes clear.

## Trade-offs

| | Star | Snowflake |
|---|---|---|
| Query joins needed | Fewer | More |
| Storage efficiency | Slightly lower | Higher |
| Update anomaly risk | Present (rare in practice) | Eliminated |
| Readability for new team | High | Lower |
| Right fit for DuckDB | Yes | Overkill |

## Extension point

If the data grows significantly (e.g. thousands of stores across many countries with hierarchical region structures), extract `region` and `segment` into a separate `dim_region` table and update `dim_store` to reference it by foreign key. The `load.py` `load_dimensions()` function is the only place that needs to change.

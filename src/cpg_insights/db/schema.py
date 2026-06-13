"""DuckDB schema DDL — star schema for CPG sales data."""

DDL = """
CREATE TABLE IF NOT EXISTS dim_product (
    sku_id       VARCHAR PRIMARY KEY,
    name         VARCHAR,
    category     VARCHAR,
    brand        VARCHAR,
    package_size VARCHAR,
    list_price   DOUBLE,
    launch_date  DATE
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_id   VARCHAR PRIMARY KEY,
    store_name VARCHAR,
    region     VARCHAR,
    city       VARCHAR,
    state      VARCHAR,
    segment    VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id     DATE PRIMARY KEY,
    year        INTEGER,
    quarter     INTEGER,
    month       INTEGER,
    month_name  VARCHAR,
    week        INTEGER,
    day_of_week INTEGER
);

CREATE TABLE IF NOT EXISTS fact_sales (
    transaction_id VARCHAR PRIMARY KEY,
    txn_date       DATE,
    store_id       VARCHAR,
    sku_id         VARCHAR,
    quantity       INTEGER,
    unit_price     DOUBLE,
    total_amount   DOUBLE,
    source         VARCHAR,
    channel        VARCHAR
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          VARCHAR PRIMARY KEY,
    run_at          TIMESTAMP,
    source          VARCHAR,
    rows_extracted  INTEGER,
    rows_valid      INTEGER,
    rows_rejected   INTEGER,
    rejection_rules VARCHAR
);

CREATE TABLE IF NOT EXISTS rejected_transactions (
    rejection_id     VARCHAR PRIMARY KEY,
    transaction_id   VARCHAR,
    source           VARCHAR,
    rejection_reason VARCHAR,
    raw_data         VARCHAR,
    rejected_at      TIMESTAMP
);
"""

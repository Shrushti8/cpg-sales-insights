"""DuckDB connection helper."""

from pathlib import Path

import duckdb

from cpg_insights.config import settings
from cpg_insights.db.schema import DDL


def get_connection(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    path = Path(db_path) if db_path else settings.db_path_abs
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    for statement in DDL.strip().split(";"):
        s = statement.strip()
        if s:
            conn.execute(s)
    return conn

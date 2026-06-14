"""Shared FastAPI dependencies — DB connection and LLM provider."""

from collections.abc import Generator

import duckdb

from cpg_insights.config import settings
from cpg_insights.db.connection import get_connection
from cpg_insights.llm import get_provider
from cpg_insights.llm.base import LLMProvider


def get_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = get_connection(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_llm() -> LLMProvider:
    return get_provider()

"""Smoke tests for project config — always present from Phase 0."""

from cpg_insights.config import Settings


def test_default_llm_provider_is_mock():
    s = Settings(llm_provider="mock")
    assert s.llm_provider == "mock"


def test_settings_accepts_gemini_provider():
    s = Settings(llm_provider="gemini")
    assert s.llm_provider == "gemini"


def test_db_path_property_returns_path_object():
    from pathlib import Path

    s = Settings(db_path="data/processed/test.duckdb")
    assert isinstance(s.db_path_abs, Path)
    assert s.db_path_abs.name == "test.duckdb"


def test_model_path_property_returns_path_object():
    from pathlib import Path

    s = Settings(model_path="models/test.pkl")
    assert isinstance(s.model_path_abs, Path)
    assert s.model_path_abs.suffix == ".pkl"

"""Shared pytest fixtures."""
import os

# Always use mock LLM in tests
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DB_PATH", "data/processed/cpg_test.duckdb")
os.environ.setdefault("MODEL_PATH", "models/revenue_model_test.pkl")

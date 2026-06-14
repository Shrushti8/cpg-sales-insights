from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    db_path: str = "data/processed/cpg.duckdb"
    model_path: str = "models/revenue_model.pkl"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def db_path_abs(self) -> Path:
        return Path(self.db_path)

    @property
    def model_path_abs(self) -> Path:
        return Path(self.model_path)


settings = Settings()

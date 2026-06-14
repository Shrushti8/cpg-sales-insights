"""LLM provider factory — resolves the active provider from settings."""

from cpg_insights.llm.base import LLMProvider
from cpg_insights.llm.mock import MockProvider


def get_provider() -> LLMProvider:
    from cpg_insights.config import settings

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set. "
                "Set the key in .env or switch to LLM_PROVIDER=mock."
            )
        from cpg_insights.llm.gemini import GeminiProvider
        return GeminiProvider(
            api_key=settings.gemini_api_key, model=settings.gemini_model
        )

    return MockProvider()

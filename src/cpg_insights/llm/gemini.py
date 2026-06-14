"""Gemini LLM provider via google-genai SDK."""

from cpg_insights.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "google-genai is not installed. Run: uv add google-genai"
            ) from exc
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model, contents=prompt
        )
        return response.text

"""Gemini LLM provider via google-genai SDK."""

from cpg_insights.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is not installed. Run: uv add google-generativeai"
            ) from exc
        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        response = self._client.generate_content(prompt)
        return response.text

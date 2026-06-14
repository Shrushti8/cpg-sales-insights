"""Mock LLM provider — deterministic, no API key needed. Used in CI and tests."""

from cpg_insights.llm.base import LLMProvider

_RESPONSES: dict[str, str] = {
    "summary": (
        "Sales are performing well across all categories. Beverages show strong summer "
        "seasonality, Snacks peak in Q4, and Personal Care maintains steady growth. "
        "West region leads in volume; Central region has the most headroom."
    ),
    "forecast_explain": (
        "The forecast reflects an upward trend driven by seasonal demand and recent "
        "sales momentum. Lag features from the previous two months anchor the projection; "
        "the confidence band widens with horizon to capture compounding uncertainty."
    ),
    "anomaly": "Revenue spike likely caused by a promotional event or bulk order.",
    "chat": "Based on the sales data, revenue is growing steadily across most categories.",
}


class MockProvider(LLMProvider):
    """Returns pre-canned responses keyed on keywords in the prompt."""

    def generate(self, prompt: str) -> str:
        lower = prompt.lower()
        if "forecast" in lower or "explain" in lower:
            return _RESPONSES["forecast_explain"]
        if "anomal" in lower or "spike" in lower or "unusual" in lower:
            return _RESPONSES["anomaly"]
        if "summary" in lower or "trend" in lower or "overview" in lower:
            return _RESPONSES["summary"]
        return _RESPONSES["chat"]

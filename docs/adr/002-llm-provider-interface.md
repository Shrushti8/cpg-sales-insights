# ADR 002 — Pluggable LLM Provider Interface

**Status:** Accepted  
**Date:** 2026-06-13

## Context

The system needs an LLM (large language model) to power the chatbot, forecast explanations, and anomaly commentary. Multiple providers are viable: Google Gemini (free via Sigmoid's Google Workspace), Anthropic Claude (paid), OpenAI GPT (paid), or a local model via Ollama. We also need CI/CD and tests to run without any API key or cost.

## Decision

Implement a `LLMProvider` abstract interface with two concrete implementations shipped: `GeminiProvider` (default) and `MockProvider` (for tests and CI). The active provider is selected via the `LLM_PROVIDER` environment variable.

## Reasons

**1. CI must be free and offline-capable.**  
Tests and the GitHub Actions pipeline run with `LLM_PROVIDER=mock`. The mock returns deterministic canned responses, so tests are fast, free, and not flaky due to API rate limits.

**2. The team inheriting this skeleton may have a different preferred provider.**  
A thin interface makes swapping providers a 30-minute task (implement `generate(prompt) -> str`, register it) rather than a codebase-wide change.

**3. Gemini is free for this evaluation via Google Workspace.**  
Per the FAQ, Sigmoid's Google Workspace includes Gemini access. Defaulting to Gemini avoids any cost for the submission demo.

## Trade-offs

| | Single hardcoded provider | Provider interface |
|---|---|---|
| Effort to build | Less | Slightly more |
| CI cost | Requires API key or mocking externally | Zero — mock is built in |
| Provider swap effort | Rewrite | Implement one method |
| Complexity added | None | One small abstraction layer |

## Extension point

To add a new provider (e.g. Claude, OpenAI, Ollama):
1. Create `src/cpg_insights/llm/your_provider.py` implementing `LLMProvider.generate(prompt: str) -> str`
2. Register it in `src/cpg_insights/llm/__init__.py`
3. Set `LLM_PROVIDER=your_provider` in `.env`

No other code changes are needed.

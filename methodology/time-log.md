# Time Log — AIA Evaluation Project

> This feeds the required methodology spreadsheet (3 sheets: Time Log, Tool Usage Summary, Decision Log).
> Log each session as you go — it's much easier than reconstructing at the end.

## Format
| Date | Duration | Area | AI Tool | What AI Generated | What I Changed/Overrode |
|------|----------|------|---------|-------------------|------------------------|

## Sessions

| Date | Duration | Area | AI Tool | What AI Generated | What I Changed/Overrode |
|------|----------|------|---------|-------------------|------------------------|
| 2026-06-13 | ~1h | Planning + Scaffold | Claude Code | Full architecture plan, all scaffold files, pyproject.toml, Makefile, .env.example | Confirmed all choices; added cheap extras (anomaly highlights, forecast explain, CSV upload, Mermaid diagram) |

## Key Decisions Log

| Decision | Options Considered | Why Chosen | AI Suggestion | Followed AI? |
|----------|--------------------|------------|---------------|--------------|
| Backend framework | FastAPI vs Django vs Flask | FastAPI: async, auto-docs at /docs, pydantic validation, fast to scaffold | FastAPI | Yes |
| UI framework | Streamlit vs React | Streamlit: all-Python, chat widget built-in, minimal boilerplate for a skeleton | Streamlit | Yes |
| Storage | DuckDB vs PostgreSQL | DuckDB: zero setup, file-based, excellent for analytics queries; Postgres = extension point | DuckDB | Yes |
| LLM provider | Gemini vs Claude vs mock | Gemini: free via Sigmoid Google Workspace; mock for CI/tests; abstracted behind interface | Gemini + mock | Yes |
| ML model | Linear/Ridge vs complex | "Linear regression that works beats a neural network that doesn't" (brief's own words) | Linear/Ridge | Yes |
| Chat safety | Raw SQL from LLM vs whitelisted queries | Never let LLM write/execute raw SQL; use whitelisted parameterized queries | Whitelisted | Yes (overrode naive approach) |

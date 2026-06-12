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
| 2026-06-13 | ~30m | DevOps — CI setup + GitHub push | Claude Code | GitHub Actions ci.yml (4 stages: lint→unit→integration→docker), gh CLI install, repo creation | Caught that workflow scope was missing from gh auth — had to re-authenticate manually; AI didn't anticipate this |
| 2026-06-13 | ~10m | Fix — lint errors | Claude Code | Auto-fixed 3 ruff errors (import ordering in config.py + conftest.py, unused pytest import) | No override needed; ran make lint locally, confirmed clean before pushing |

## Key Decisions Log

| Decision | Options Considered | Why Chosen | AI Suggestion | Followed AI? |
|----------|--------------------|------------|---------------|--------------|
| Backend framework | FastAPI vs Django vs Flask | FastAPI: async, auto-docs at /docs, pydantic validation, fast to scaffold | FastAPI | Yes |
| UI framework | Streamlit vs React | Streamlit: all-Python, chat widget built-in, minimal boilerplate for a skeleton | Streamlit | Yes |
| Storage | DuckDB vs PostgreSQL | DuckDB: zero setup, file-based, excellent for analytics queries; Postgres = extension point | DuckDB | Yes |
| LLM provider | Gemini vs Claude vs mock | Gemini: free via Sigmoid Google Workspace; mock for CI/tests; abstracted behind interface | Gemini + mock | Yes |
| ML model | Linear/Ridge vs complex | "Linear regression that works beats a neural network that doesn't" (brief's own words) | Linear/Ridge | Yes |
| Chat safety | Raw SQL from LLM vs whitelisted queries | Never let LLM write/execute raw SQL; use whitelisted parameterized queries | Whitelisted | Yes (overrode naive approach) |
| GitHub auth scope | Default gh auth vs workflow scope | CI pushes .github/workflows/ files which need explicit workflow scope — GitHub blocks it otherwise | Claude didn't know upfront; discovered during push failure | No — had to manually re-auth with -s workflow flag |

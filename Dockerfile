# ── builder stage: install all dependencies ────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e ".[dev]"


# ── runtime stage: lean image with only the app ────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source
COPY src/ ./src/

# Directories the app writes to at runtime
RUN mkdir -p data/raw data/processed models

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "cpg_insights.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

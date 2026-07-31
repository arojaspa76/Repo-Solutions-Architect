# Project:     GenAIDemo
# Component:   Backend Dockerfile
# Description: Multi-stage build for the FastAPI service using uv. Build context is
#              the repo root because the app imports the root-level `src` package.
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

FROM python:3.12-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

COPY src ./src
COPY configs ./configs
COPY apps/api/src ./apps/api/src

ENV PYTHONPATH="/app"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD uv run python -c "import httpx; r=httpx.get('http://localhost:8000/api/v1/health'); exit(0 if r.status_code==200 else 1)"

CMD ["uv", "run", "uvicorn", "main:app", "--app-dir", "apps/api/src", "--host", "0.0.0.0", "--port", "8000"]

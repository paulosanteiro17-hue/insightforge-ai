# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.12.17 AS uv

FROM python:3.11-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN python -m pip uninstall --yes pip setuptools wheel \
    && addgroup --system --gid 10001 insightforge \
    && adduser --system --uid 10001 --ingroup insightforge insightforge \
    && mkdir -p /app/.data/private \
    && chown -R insightforge:insightforge /app

COPY --from=builder --chown=insightforge:insightforge /app/.venv /app/.venv
COPY --chown=insightforge:insightforge alembic.ini ./alembic.ini
COPY --chown=insightforge:insightforge alembic ./alembic

USER insightforge
EXPOSE 8000
CMD ["uvicorn", "insightforge.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log", "--no-server-header"]

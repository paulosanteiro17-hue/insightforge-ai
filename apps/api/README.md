# InsightForge AI API

This package contains the FastAPI application and PostgreSQL persistence layer for
InsightForge AI. It uses a Python `src` layout, SQLAlchemy 2 async sessions, and
Alembic migrations.

## Local commands

From the repository root:

```text
uv sync --project apps/api --group dev --no-editable
uv run --project apps/api --no-sync alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api --no-sync uvicorn --app-dir apps/api/src insightforge.main:app --reload --reload-dir apps/api/src --port 8000
uv run --project apps/api --no-sync pytest apps/api
```

The application reads shared values from the repository `.env` file and accepts
environment variables documented in `.env.example`. PostgreSQL is required for
integration tests; fast unit and API contract tests do not connect to a database.
The explicit application directory and pytest `pythonpath` ensure local commands
always exercise the working tree after a Windows-safe non-editable dependency sync.

## Security model

Browser authentication uses opaque server-side sessions. Only SHA-256 token digests
are stored. Unsafe cookie-authenticated requests require a matching CSRF cookie and
header, an allowed browser origin, and a valid session-bound or signed pre-auth token.
Tenant routes require `X-Organization-ID`, validated against the active user before
any tenant data is queried.

# Contributing to InsightForge AI

Thank you for helping improve InsightForge AI. This portfolio project follows production-oriented review and verification standards.

## Development principles

- Write all source code, identifiers, documentation, sample data, and user-facing copy in English.
- Keep organization scoping explicit in every tenant-owned backend operation.
- Add tests for success, validation, authorization, and cross-tenant failure paths.
- Never commit secrets, local databases, uploaded files, build outputs, or dependency directories.
- Do not add visible controls or routes until their behavior and error states work.

## Local workflow

1. Create local environment files from `.env.example`.
2. Install JavaScript dependencies with `npm install`.
3. Install Python dependencies with `uv sync --project apps/api --all-groups --no-editable`.
4. Start PostgreSQL and the applications as documented in `README.md`.
5. Run `npm run verify` before opening a pull request.

## Pull requests

Keep changes focused and explain the business behavior, security impact, tests run, and any documentation updates. A change is not complete when required verification is skipped or failing.

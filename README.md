# InsightForge AI

[![CI](https://github.com/paulosanteiro17-hue/insightforge-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/paulosanteiro17-hue/insightforge-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-2563EB.svg)](LICENSE)
[![Security review](https://img.shields.io/badge/security-reviewed-15803D.svg)](docs/SECURITY_AUDIT.md)

InsightForge AI is a full-stack, multi-tenant SaaS analytics platform for growing businesses. It turns sales, customer, product, and order data into consistent KPIs, interactive dashboards, durable reports, and grounded AI-assisted explanations.

The product is built as a deployable system rather than a collection of static screens: a Next.js application talks to a typed FastAPI API through a same-origin proxy, PostgreSQL is the source of truth, and a restart-safe worker processes imports, insights, reports, exports, and cleanup jobs.

> **Verified release candidate — August 13, 2026:** the complete local product, migration path, production builds, automated suites, and integrated Docker Compose stack pass. A public deployment URL has not been published, so this repository does not claim a live production release.

## Product highlights

- One-click, isolated demo workspaces with realistic commerce history and no reusable privileged credentials.
- Opaque server-side sessions, double-submit CSRF, tenant-scoped authorization, Owner/Admin/Member roles, and final-owner protection.
- Responsive overview and analytics dashboards with consistent period comparisons, customer acquisition, category contribution, product ranking, and order status views.
- Searchable and filterable customers, products, sales, and order detail workflows.
- Bounded CSV uploads with safe preview, validation errors, explicit commit, private retention, and worker-backed processing.
- Durable AI Insight and Weekly Business Summary jobs grounded in calculated aggregate metrics.
- Ask Your Data intent routing that never executes model-authored SQL and cites the metrics used in each answer.
- Worker-generated CSV and JSON reports with tenant checks, formula-safe exports, expiration, and authorized downloads.
- Invitation acceptance, member administration, organization onboarding, profile/preferences, data exports, and deletion controls.
- No-charge demo billing with plan limits, usage, invoice records, and idempotent simulated plan changes. No payment provider or real charge is used.
- Deterministic AI by default, with an optional OpenAI Responses adapter configured entirely on the server.

## Screenshots

<table>
  <tr>
    <td><img src="docs/screenshots/01-landing-page.png" alt="InsightForge AI landing page" /></td>
    <td><img src="docs/screenshots/02-overview-dashboard.png" alt="InsightForge AI overview dashboard" /></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/03-analytics.png" alt="InsightForge AI analytics workspace" /></td>
    <td><img src="docs/screenshots/04-customers.png" alt="InsightForge AI customer directory" /></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/05-ai-insights.png" alt="Grounded AI insight cards" /></td>
    <td><img src="docs/screenshots/06-ask-your-data.png" alt="Ask Your Data grounded answer" /></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/07-reports.png" alt="InsightForge AI generated report history" /></td>
    <td><img src="docs/screenshots/08-mobile-dashboard.png" alt="InsightForge AI mobile dashboard" /></td>
  </tr>
</table>

The checked capture workflow and publication notes are in [Portfolio presentation](docs/PORTFOLIO.md).

## Architecture

```mermaid
flowchart LR
    Browser[Browser] -->|same-origin /api/v1| Web[Next.js web]
    Web --> API[FastAPI API]
    API --> Services[Application services]
    Services --> Repositories[Tenant-scoped repositories]
    Repositories --> DB[(PostgreSQL)]
    Services --> Jobs[(Durable job queue)]
    Jobs --> DB
    Worker[Python worker] -->|leases jobs| Jobs
    Worker --> Storage[(Private local storage)]
    Worker -. optional aggregate context .-> OpenAI[OpenAI Responses API]
```

The API is a modular monolith. Routers translate HTTP, services own use cases and transactions, repositories enforce organization context, and PostgreSQL constraints provide a second tenant-integrity layer. The API and worker share domain code but run as independent processes.

The analytics engine owns metric definitions. Dashboards, reports, deterministic insights, and optional AI explanations consume the same calculated snapshots, preventing each surface from inventing different business math.

See [Architecture](docs/ARCHITECTURE.md), [Data model](docs/DATA_MODEL.md), and [Architecture decisions](docs/DECISIONS.md) for the deeper design.

## Technology stack

| Layer         | Technology                                                                 |
| ------------- | -------------------------------------------------------------------------- |
| Web           | Next.js 16, React 19, TypeScript, Tailwind CSS 4, TanStack Query, Recharts |
| API           | Python 3.11, FastAPI, Pydantic, async SQLAlchemy 2, Alembic                |
| Data and jobs | PostgreSQL 17, transactional job enqueueing, lock/lease worker claims      |
| AI            | Deterministic provider and optional OpenAI Responses adapter               |
| Testing       | Vitest, Testing Library, Playwright, axe-core, pytest, HTTPX               |
| Quality       | ESLint, Prettier, Ruff, strict mypy, content and secret audits             |
| Delivery      | Multi-stage Docker images, Docker Compose, GitHub Actions                  |

## Quick start with Docker

### Prerequisites

- Docker Desktop with Docker Compose v2
- Git

### Run the integrated stack

```bash
cp .env.example .env
docker compose up --build --wait
```

Open `http://localhost:3000`, select **Explore the live demo**, and then select **Open Demo Owner workspace**. Each live demo request creates an isolated organization and seed revision.

The stack exposes:

- Web application: `http://localhost:3000`
- FastAPI service: `http://localhost:8000`
- Development OpenAPI UI: `http://localhost:8000/api/docs`
- PostgreSQL: `127.0.0.1:5432`

The one-shot `migrate` service applies Alembic before the API and worker become ready. Check the stack with:

```bash
docker compose ps
docker compose logs --no-color api worker web
```

Stop services without deleting local data:

```bash
docker compose down
```

Use `docker compose down --volumes` only when intentionally removing the local database and private artifacts.

## Local development without Docker

### Prerequisites

- Node.js 24 and npm 11
- Python 3.11
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 17-compatible database

### Install and configure

```bash
npm ci
uv sync --project apps/api --all-groups --locked
cp .env.example .env
```

For processes started directly on the host, use a host database URL and storage path rather than the Compose service names:

```dotenv
DATABASE_URL=postgresql+asyncpg://insightforge:local-development-only@127.0.0.1:5432/insightforge
INSIGHTFORGE_PRIVATE_STORAGE_PATH=.data/private
API_INTERNAL_URL=http://127.0.0.1:8000
```

Apply migrations and start the web, API, and worker processes:

```bash
uv run --project apps/api --no-sync alembic -c apps/api/alembic.ini upgrade head
npm run dev
```

Individual process commands are available as `npm run dev:web`, `npm run dev:api`, and `npm run dev:worker`.

## Environment configuration

`.env.example` is the canonical local template. Important settings include:

| Area              | Variables                                                                                         | Notes                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Database          | `DATABASE_URL`                                                                                    | Async PostgreSQL URL; use TLS in hosted environments                         |
| Session security  | `INSIGHTFORGE_CSRF_SIGNING_KEY`, `INSIGHTFORGE_SESSION_COOKIE_SECURE`                             | Replace the local signing key and require secure cookies outside development |
| Browser trust     | `INSIGHTFORGE_ALLOWED_ORIGINS`, `INSIGHTFORGE_ALLOWED_HOSTS`, `INSIGHTFORGE_CSRF_ALLOWED_ORIGINS` | Exact allowlists; no production wildcard                                     |
| Private artifacts | `INSIGHTFORGE_PRIVATE_STORAGE_PATH`                                                               | Must be persistent and private when deployed                                 |
| Request limits    | `INSIGHTFORGE_REQUEST_MAX_BYTES`, `INSIGHTFORGE_UPLOAD_MAX_BYTES`, `INSIGHTFORGE_UPLOAD_MAX_ROWS` | Global 12 MiB body cap; uploads default to 10 MiB and 50,000 data rows       |
| AI provider       | `INSIGHTFORGE_AI_PROVIDER`                                                                        | `deterministic` by default; set explicitly to enable the optional adapter    |
| OpenAI            | `INSIGHTFORGE_OPENAI_API_KEY`, `INSIGHTFORGE_OPENAI_MODEL`, `INSIGHTFORGE_OPENAI_TIMEOUT_SECONDS` | Server-side only; never exposed through `NEXT_PUBLIC_*`                      |
| Web proxy         | `API_INTERNAL_URL`, `PUBLIC_WEB_URL`, `NEXT_PUBLIC_API_BASE_URL`                                  | Exact configured origins; the browser normally uses same-origin `/api/v1`    |

No OpenAI key is required for the complete demo and test path. Billing is intentionally a no-charge local service and has no payment credentials.

## Verification

Run the repository-wide local quality gate:

```bash
npm run verify
```

This runs English/encoding and secret audits, formatting checks, frontend and backend linting, strict type checks, unit/integration tests, and production builds.

Additional integrated gates:

```bash
npm run test:e2e
docker compose config --quiet
docker compose build
docker compose up --detach --wait
```

### Verified baseline

Results recorded on August 13, 2026:

| Gate                                        |                                                           Result |
| ------------------------------------------- | ---------------------------------------------------------------: |
| Frontend Vitest                             |                                                 30 passing tests |
| Backend pytest with migrated PostgreSQL     |                                                154 passing tests |
| Mock browser journeys                       | 14 passing tests, including axe accessibility and console checks |
| Live production-stack browser journey       |                          1 passing end-to-end worker/report flow |
| npm high-severity dependency audit          |                                                0 vulnerabilities |
| Python production dependency audit          |                                                0 vulnerabilities |
| Bandit and Semgrep security scans           |                                                       0 findings |
| Runtime-image high/critical scan            |                                        0 fixable vulnerabilities |
| OWASP ZAP passive baseline                  |                                     0 failures; 59 checks passed |
| Ruff, mypy, ESLint, Prettier, TypeScript    |                                                          Passing |
| Next.js and Python package builds           |                                                          Passing |
| Docker images, migrations, readiness checks |                                                          Passing |

The conditional live test can be run against the Compose stack with:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_LIVE_STACK=1 \
npx playwright test apps/web/e2e/live-stack.spec.ts --config apps/web/playwright.config.ts --workers=1
```

## API surface

The versioned `/api/v1` API includes:

- authentication, session rotation, CSRF bootstrap, password reset, and one-click demo creation;
- organizations, onboarding, usage, exports, deletion, and demo lifecycle controls;
- user profile and preference management;
- customers, products, orders, status transitions, and tenant-scoped metrics;
- canonical analytics views and snapshot metadata;
- insights, weekly summaries, Ask Your Data capabilities/history, and background generation jobs;
- report templates, generation status, and authorized downloads;
- staged imports, preview/errors, commit/cancel, and templates;
- team members, invitations, public invitation preview, acceptance, revocation, and role changes;
- plans, subscriptions, usage, simulated billing intents, and demo invoice history.

Responses use consistent envelopes and RFC 9457-style problem details with request IDs. Mutation routes use CSRF and idempotency controls where replay safety matters. See [API reference](docs/API.md) for contracts and [Routes](docs/ROUTES.md) for the product journey map.

## Security model

The implementation includes:

- Argon2 password hashing and opaque, revocable server-side sessions;
- Secure/HttpOnly/SameSite cookie settings with production startup validation;
- double-submit CSRF with signed tokens and strict origin checks;
- rate limits for authentication and demo creation;
- explicit organization context, permission checks, concealed cross-tenant lookups, and composite tenant foreign keys;
- bounded uploads, file signature checks, private storage, safe previews, formula-safe exports, and retention cleanup;
- allowlisted analytical intents with no arbitrary SQL, tools, URLs, or tenant selection;
- structured redacted logs, request IDs, audit events, and repository secret scanning;
- global request-body limits, fixed configured proxy origins, and short idle sessions;
- CSP, HSTS on HTTPS deployments, host validation, exact CORS/CSRF allowlists, and additional browser security headers;
- read-only, capability-free application containers and full-SHA-pinned CI actions.

See [Security](docs/SECURITY.md) for the standing control model and [Security audit](docs/SECURITY_AUDIT.md) for the completed review, remediations, scan evidence, and residual risks.

## Repository structure

```text
.
├── apps/
│   ├── api/                 FastAPI application, worker, Alembic, and pytest
│   └── web/                 Next.js application, Vitest, Playwright, and axe
├── data/samples/            Safe English CSV import examples
├── docs/                    Architecture, API, security, deployment, and screenshots
├── scripts/                 Content and secret audits
├── .github/workflows/       CI quality gates
├── compose.yaml             Integrated local production-style stack
└── .env.example             Non-secret configuration template
```

The detailed tree and module responsibilities are documented in [Repository structure](docs/REPOSITORY_STRUCTURE.md).

## Deployment status

The repository provides portable production images, a controlled migration command, health/readiness endpoints, persistent private-storage configuration, and a deployment checklist. It has been verified locally as an integrated production-style stack.

No public domain is currently published. Hosted deployment still requires real TLS domains, managed PostgreSQL, a persistent private artifact volume or a new remote-storage adapter, environment-specific secrets, backups, observability, and completion of the live smoke checklist in [Deployment](docs/DEPLOYMENT.md).

## Documentation

| Document                                    | Purpose                                                              |
| ------------------------------------------- | -------------------------------------------------------------------- |
| [Architecture](docs/ARCHITECTURE.md)        | Runtime boundaries, workflows, analytics, jobs, and deployment model |
| [API reference](docs/API.md)                | Versioned resources, permissions, envelopes, and behavior            |
| [Data model](docs/DATA_MODEL.md)            | Tables, constraints, ownership, and retention                        |
| [Security](docs/SECURITY.md)                | Threat model, controls, assumptions, and residual risk               |
| [Security audit](docs/SECURITY_AUDIT.md)    | Reviewed findings, remediations, scan evidence, and limitations      |
| [Deployment](docs/DEPLOYMENT.md)            | Configuration, migrations, health checks, rollback, and smoke gates  |
| [Architecture decisions](docs/DECISIONS.md) | Accepted design choices and consequences                             |
| [Implementation record](docs/PLAN.md)       | Delivered phases, evidence, limitations, and optional future work    |
| [Portfolio presentation](docs/PORTFOLIO.md) | Case-study copy, screenshot set, and publication checklist           |

## Known deployment limitations

- There is no verified public deployment URL yet.
- The included private artifact adapter targets a local or mounted persistent filesystem; remote object storage requires an additional adapter.
- Billing is deliberately simulated and cannot collect payments.
- Email delivery is not configured; invitation links and reset tokens are surfaced only in safe development/demo workflows.
- OpenAI output depends on the configured account, model availability, and provider policy; deterministic mode remains the supported credential-free path.

## License

Released under the [MIT License](LICENSE).

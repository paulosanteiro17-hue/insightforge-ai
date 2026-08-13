# Repository Structure

InsightForge AI uses a small monorepo. The web application and API/worker package build independently while sharing one review, CI, and local-development workflow.

```text
insightforge-ai/
├── apps/
│   ├── api/
│   │   ├── alembic/                 # Versioned PostgreSQL migrations
│   │   ├── scripts/                 # Worker and maintenance entry points
│   │   ├── src/insightforge/
│   │   │   ├── ai/                  # Deterministic and OpenAI provider boundary
│   │   │   ├── analytics/           # Canonical KPI calculations
│   │   │   ├── api/                 # FastAPI health and v1 routers
│   │   │   ├── core/                # Settings, security, errors, logging, policies
│   │   │   ├── db/                  # Async database session and metadata
│   │   │   ├── imports/             # CSV parsing and validation
│   │   │   ├── models/              # SQLAlchemy persistence models
│   │   │   ├── repositories/        # Tenant-scoped persistence operations
│   │   │   ├── schemas/             # Pydantic request/response contracts
│   │   │   ├── services/            # Transactions and application workflows
│   │   │   ├── storage/             # Private local filesystem adapter
│   │   │   ├── worker/              # Durable job handlers and runner
│   │   │   └── main.py              # FastAPI composition root
│   │   ├── tests/                    # Unit, API, and PostgreSQL integration tests
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── uv.lock
│   └── web/
│       ├── e2e/                      # Playwright journeys, accessibility, live stack
│       ├── public/                   # Static web assets
│       ├── src/
│       │   ├── app/                  # Next.js App Router pages and layouts
│       │   ├── components/           # Marketing, product, data, and UI components
│       │   ├── content/              # Centralized English marketing content
│       │   ├── lib/                  # API adapters, contracts, formatters, utilities
│       │   └── test/                 # Vitest setup and shared test helpers
│       ├── Dockerfile
│       ├── next.config.ts
│       ├── package.json
│       └── playwright.config.ts
├── data/samples/                     # Safe English CSV import examples
├── docs/                             # Design, security, deployment, and screenshots
├── scripts/                          # Content/encoding and credential audits
├── .github/workflows/ci.yml          # Web, API, and integrated Compose gates
├── .env.example                      # Non-secret configuration contract
├── compose.yaml                      # Web, API, worker, migration, and PostgreSQL
├── package.json                      # npm workspace and root commands
└── README.md
```

## Application boundaries

### Web

The web application owns presentation, browser interaction, accessibility, route-level states, and cached server state. It does not implement authorization or business metrics. FastAPI is authoritative for both.

Server Components render static and initial content where useful. Client Components are limited to interactive charts, forms, dialogs, filters, and TanStack Query state. The runtime adapter boundary supports deterministic browser tests without changing production page code.

### API and worker

HTTP routers parse contracts and delegate to services. Services enforce policies and coordinate transactions. Repositories contain persistence details and require explicit organization context for tenant-owned data. Analytics functions accept typed parameters and return typed aggregates.

The API package uses a `src` layout. The API and worker run from the same versioned package/image, but only the worker leases durable jobs and performs imports, reports, insight generation, exports, demo expiration, and cleanup.

### Contracts

FastAPI/Pydantic schemas are authoritative at the HTTP boundary. The web application maintains focused TypeScript contracts and adapters for the consumed surface. Contract behavior is exercised through backend route tests, frontend adapter tests, and a live full-stack Playwright journey.

## Naming conventions

- All code, database identifiers, routes, documentation, tests, sample data, and visible interface copy are English.
- Python modules/functions use `snake_case`; Python and TypeScript types use `PascalCase`.
- TypeScript values use `camelCase`; React components use `PascalCase`.
- REST paths use plural kebab-case resources under `/api/v1`.
- Database tables and columns use `snake_case`.
- API environment variables use the `INSIGHTFORGE_` prefix; `NEXT_PUBLIC_` is reserved for values safe to expose to browsers.

## Root commands

| Command             | Purpose                                                 |
| ------------------- | ------------------------------------------------------- |
| `npm run dev`       | Run web, API, and worker development processes          |
| `npm run lint`      | Run frontend and backend linting                        |
| `npm run typecheck` | Run TypeScript and strict Python type checks            |
| `npm run test`      | Run frontend and backend suites                         |
| `npm run test:e2e`  | Run mock Playwright journeys and accessibility checks   |
| `npm run build`     | Build the production web application and Python package |
| `npm run verify`    | Run all non-destructive repository quality gates        |

Docker is optional for focused frontend work. `docker compose up --build --wait` is the canonical integrated environment.

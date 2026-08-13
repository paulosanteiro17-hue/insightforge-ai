# InsightForge AI Portfolio Kit

This document contains portfolio copy and presentation guidance for the completed, verified repository. Keep claims synchronized with `docs/PLAN.md`; do not publish a deployment URL, test result, or feature claim before it has been verified.

## Project title

**AI-Powered SaaS Analytics Dashboard**

Product name: **InsightForge AI**

## Short description

InsightForge AI is a multi-tenant SaaS analytics platform that turns commerce data into clear KPIs, interactive dashboards, controlled reports, and actionable AI-assisted business insights. It combines a polished Next.js interface with a tenant-safe FastAPI/PostgreSQL backend, deterministic analytics, secure CSV ingestion, and an optional OpenAI provider.

## Full Upwork portfolio description

### The business problem

Growing businesses often have customer, sales, product, and order data spread across disconnected exports and operational tools. Teams can see individual transactions, but they struggle to answer basic performance questions consistently: What is driving revenue? Which products are gaining momentum? Are customer acquisition and average order value improving? Where did an unusual drop begin?

### The solution

I designed and built InsightForge AI as an end-to-end SaaS analytics product. Organizations can onboard into an isolated workspace, load a realistic demo dataset or validate and import structured CSV data, and explore a responsive analytics experience across revenue, orders, customers, conversion, product performance, and growth.

The platform calculates business metrics in a deterministic backend analytics layer before AI interpretation. AI Insights and Ask Your Data receive only bounded aggregate context and map questions to controlled analytical functions; the model never receives unrestricted database access and never executes generated SQL. When no provider key is configured, a deterministic provider keeps the complete evaluation path useful and honest.

### My role and contribution

I owned the complete product engineering lifecycle:

- product and domain modeling;
- frontend architecture and responsive UI/UX;
- FastAPI service design and REST contracts;
- PostgreSQL schema, constraints, indexes, and migrations;
- secure authentication, CSRF protection, role authorization, and tenant isolation;
- analytics calculations and realistic 12-month seed data;
- bounded CSV validation and durable background workflows;
- provider-neutral AI and a no-charge demo billing service;
- automated backend, frontend, and end-to-end testing;
- Docker, CI quality gates, security review, deployment design, and technical documentation.

### Key features

- Professional SaaS landing page, onboarding, authentication, and one-click demo access.
- Organization-scoped workspaces with Owner, Admin, and Member capabilities.
- Responsive overview and analytics dashboards with period comparisons and interactive charts.
- Customer, product, sales, and order workflows with search, filtering, sorting, pagination, details, and historical metrics.
- Staged CSV upload, validation, safe preview, explicit commit, error reporting, and import history.
- Deterministic AI Insights for growth, warnings, opportunities, performance, and anomalies.
- Safe Ask Your Data intent routing without arbitrary SQL or model-selected organization context.
- Weekly Business Summary and reusable, filterable report generation with formula-safe CSV exports.
- No-charge Demo Billing with plan limits, usage, invoice records, and simulated plan changes.
- Structured errors and logs, request IDs, audit events, private artifact storage, and durable PostgreSQL-backed jobs.
- Automated quality gates across formatting, linting, type checks, migrations, tests, production builds, and integrated containers.

### Architecture

InsightForge AI is a modular monorepo with independently deployable applications:

- **Web:** Next.js App Router, React, TypeScript, Tailwind CSS, TanStack Query, and Recharts.
- **API:** Python, FastAPI, Pydantic, async SQLAlchemy, and Alembic.
- **Data:** PostgreSQL with UUID keys, fixed-precision money, composite tenant foreign keys, constraints, indexes, and derived metric snapshots.
- **Workers:** durable jobs claimed with PostgreSQL locks and leases, avoiding an unnecessary broker in the first release.
- **AI:** deterministic provider by default, optional OpenAI adapter, schema-validated output, and controlled analytical intents.
- **Delivery:** Docker Compose locally and GitHub Actions for repeatable quality gates; provider-neutral container deployment with a documented Vercel/Render/Neon reference topology.

### Technical challenges addressed

1. **Tenant isolation:** every organization-owned query requires validated tenant context, while composite database constraints prevent records from referencing another organization's parent rows.
2. **Metric consistency:** dashboards, reports, exports, deterministic insights, and optional AI explanations consume one canonical analytics engine rather than reimplementing business math.
3. **Secure AI behavior:** questions resolve to allow-listed functions and typed parameters; no model-authored SQL, code, URLs, tools, or tenant identifiers are executed.
4. **Reliable imports:** uploads are bounded, privately retained, validated twice, previewed before commit, and applied transactionally through restart-safe durable jobs.
5. **Portfolio-safe evaluation:** one-click demo access creates an isolated, restricted Demo Owner experience with realistic history and no reusable privileged password or real payment requirement.

### Demonstrated result

The project demonstrates the ability to take a SaaS product from ambiguous business goals through architecture, implementation, security controls, testing, containerization, deployment planning, and recruiter-focused presentation. It is intentionally built as one coherent product rather than a collection of disconnected interface screens.

Do not add numerical performance, coverage, or availability claims here unless the repository includes repeatable evidence for them.

## Technology list

- Next.js
- React
- TypeScript
- Tailwind CSS
- TanStack Query
- Recharts
- Vitest and React Testing Library
- Playwright
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- pytest
- Ruff and mypy
- Docker and Docker Compose
- GitHub Actions
- OpenAI-compatible provider abstraction
- No-charge demo billing service

## Suggested Upwork skills and tags

Use the most relevant tags allowed by the selected Upwork category:

- Full-Stack Development
- SaaS Development
- Web Application Development
- Next.js
- React
- TypeScript
- Python
- FastAPI
- PostgreSQL
- RESTful API
- Database Design
- API Integration
- OpenAI API
- Artificial Intelligence
- Data Visualization
- Dashboard
- Business Intelligence
- Docker
- Automated Testing
- CI/CD
- Software Architecture

## Suggested Upwork project summary

> Built an end-to-end, multi-tenant SaaS analytics platform using Next.js, TypeScript, FastAPI, and PostgreSQL. The product imports business data, calculates consistent KPIs, visualizes trends, generates secure AI-assisted insights, and supports controlled natural-language analytics without arbitrary SQL. I implemented the domain model, authentication and role authorization, tenant isolation, durable CSV workflows, deterministic demo mode, automated tests, Docker environment, CI gates, and production deployment architecture.

## Repository front-page pitch

**Business data is useful only when a team can act on it.** InsightForge AI consolidates sales, customer, product, and order signals into one tenant-safe analytics workspace, then turns calculated metrics into concise explanations, opportunities, and risks.

For a 60-second review, lead with:

1. the landing hero and product value;
2. a direct one-click demo path;
3. the overview screenshot with meaningful trends;
4. the architecture diagram and backend/data/security summary;
5. exact verification commands and CI status;
6. the AI safety model: aggregates and allow-listed intents, never arbitrary SQL.

## Screenshot art direction

Use a consistent seeded organization, reporting period, viewport, and data revision. Close developer tools, browser extensions, and personal bookmarks. Do not include real email addresses, API keys, internal URLs, local filesystem paths, or unverified alerts.

### Desktop settings

- Browser viewport: 1440 × 1024 or 1440 × 1100.
- Device scale: 1.
- Preferred range for overview/analytics: Last 90 days unless a specific chart is clearer at Year to date.
- Capture PNG at native resolution.
- Keep the product navigation visible when it adds context.

### Mobile settings

- Viewport: 390 × 844 (modern phone) and optionally 768 × 1024 (tablet).
- Capture the responsive navigation deliberately open in one secondary shot, not every shot.
- Confirm no horizontal overflow, clipped tooltip, unreadable axis, or hover-only action.

## Required screenshot checklist

- [x] **01 — Landing page:** hero, value proposition, product preview, AI explanation, workflow, pricing preview, CTA, and footer.
- [x] **02 — Overview dashboard:** KPI cards, revenue trend, comparison, top products/categories, order status, recent transactions, and Weekly Business Summary.
- [x] **03 — Analytics:** range controls and detailed trend/contribution views with meaningful comparisons.
- [x] **04 — Customers:** polished searchable/filterable list with plausible names, segments, total spend, and recent purchase data.
- [x] **05 — AI Insights:** mixed Growth, Warning, Opportunity, Performance, and Anomaly cards with supporting metrics and generation metadata.
- [x] **06 — Ask Your Data:** example question, concise answer, cited supporting metrics, applied range, and safe follow-up prompts.
- [x] **07 — Reports:** report generation, history, filters, and ready export actions.
- [x] **08 — Mobile dashboard:** responsive KPI cards, charts, summary, compact navigation, and no clipped content.

### Valuable secondary screenshots

- [ ] Customer detail with order history and lifetime metrics.
- [ ] Product performance view with revenue/unit trends.
- [ ] CSV validation preview with both accepted rows and a safe error report example.
- [ ] Team permissions and invitation management.
- [ ] Demo Billing plan comparison with explicit no-charge labeling.
- [ ] Architecture diagram or passing CI quality gates for a technical carousel slide.

## Screenshot acceptance checks

- [x] Every visible word is English and free of placeholder/tutorial copy.
- [x] The seeded data looks plausible and tells a coherent 12-month story.
- [x] KPI totals and chart values agree for the selected range.
- [x] Tooltips, focus rings, status labels, legends, and empty/loading states are styled consistently.
- [x] No dead control, `Coming soon`, `TODO`, broken image, loading spinner, error toast, or console error is present.
- [x] Personal data and secrets are absent.
- [x] Desktop and mobile images have consistent naming under `docs/screenshots/`.
- [x] README image links target the reviewed files under `docs/screenshots/`.

## Suggested screenshot filenames

```text
docs/screenshots/01-landing-page.png
docs/screenshots/02-overview-dashboard.png
docs/screenshots/03-analytics.png
docs/screenshots/04-customers.png
docs/screenshots/05-ai-insights.png
docs/screenshots/06-ask-your-data.png
docs/screenshots/07-reports.png
docs/screenshots/08-mobile-dashboard.png
```

## Interview talking points

- Why a modular monolith was a stronger first-release choice than microservices.
- How opaque sessions, double-submit CSRF, roles, demo restrictions, and tenant context fit together.
- Why composite tenant foreign keys matter even when every repository already filters by organization.
- How deterministic analytics makes AI explanations testable and keeps the product useful without credentials.
- Why Ask Your Data resolves controlled intents instead of asking a model to write SQL.
- How PostgreSQL-backed leases make background workflows durable without introducing Redis/Celery prematurely.
- How realistic seed seasonality, weak periods, spikes, and churn signals make analytics and AI screenshots credible.
- Which release gates distinguish compiled code from a verified, deployable product.

## Publication checklist

- [ ] Public deployment URL passed the production smoke checklist in `docs/DEPLOYMENT.md`.
- [x] Demo access reaches a resettable isolated organization without reusable privileged credentials.
- [x] README reflects only implemented features and contains working screenshot links.
- [ ] CI is green for the published commit.
- [ ] License, environment example, architecture, API, security, and deployment documents are current.
- [ ] No secrets, local databases, uploads, build artifacts, dependency directories, or personal data are tracked.
- [ ] GitHub repository description and topics match the project title and technology list.
- [x] Upwork description contains no unverified performance or completion claim.

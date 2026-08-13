# InsightForge AI Architecture Decisions

This file records the decisions implemented by the release candidate. A conflicting material change should add a superseding ADR rather than silently changing the rationale.

## ADR-001 — Use a modular monorepo

**Status:** Accepted

Keep Next.js and FastAPI/worker applications in one repository with independent builds and shared root quality commands. This keeps product/API/schema review atomic while preserving deployable process boundaries.

## ADR-002 — Use Next.js, FastAPI, and PostgreSQL

**Status:** Accepted

Next.js App Router provides the server/client rendering model and polished product experience. FastAPI/Pydantic provides explicit contracts and async Python service composition. PostgreSQL provides transactions, constraints, fixed-precision numerics, JSON support, locks, and the durable initial job queue.

## ADR-003 — Use a modular-monolith backend

**Status:** Accepted

Routers translate HTTP, services own use cases/transactions, repositories own scoped persistence, and domain modules own analytics/import/AI behavior. The API and worker share this package. Microservices would add distributed consistency and operational cost before there is measured need.

## ADR-004 — Use async SQLAlchemy 2 and Alembic

**Status:** Accepted

Use typed declarative mappings, explicit `select()` calls, one async session per request/job unit, and deliberate eager loading. Alembic is the only schema migration mechanism; migrations run as one controlled release step.

## ADR-005 — Use shared-schema tenant ownership with layered controls

**Status:** Accepted

Every organization-owned operation starts from authenticated `TenantContext`. Repositories filter by organization, records copy `organization_id`, and composite tenant constraints prevent cross-tenant parent references. Cross-tenant lookups are concealed. PostgreSQL RLS is deferred and not claimed.

## ADR-006 — Use opaque sessions and signed double-submit CSRF

**Status:** Accepted

Store only session-token digests, use HttpOnly cookies, enforce idle/absolute expiry and revocation, and bind CSRF-token digests to sessions. HMAC-sign pre-authentication CSRF tokens and validate exact origins. This suits same-origin browser SaaS and avoids exposing bearer tokens to JavaScript.

## ADR-007 — Keep shareable view state in URLs

**Status:** Accepted

Date range, search, sort, filter, page, and selected view state that changes the visible result belongs in validated query parameters. TanStack Query owns server state; React owns local ephemeral/form state. No general global client store is introduced.

## ADR-008 — Maintain one canonical analytics engine

**Status:** Accepted

Backend metric definitions own time-zone boundaries, eligible orders, refunds, money precision, comparisons, missing data, and division by zero. Dashboards, reports, deterministic insights, summaries, and Ask Your Data consume the same engine/snapshots.

## ADR-009 — Use deterministic AI by default with an optional OpenAI adapter

**Status:** Accepted

The full product must remain useful and testable without paid credentials. Deterministic findings use canonical aggregate metrics. The optional OpenAI Responses boundary receives only bounded aggregate findings and must return schema-valid output. Provider/model/prompt/generation metadata is persisted.

## ADR-010 — Never execute model-authored SQL

**Status:** Accepted

Ask Your Data maps text to a small set of allowlisted analytics intents and typed parameters. The application calls trusted analytics functions and cites their results. Arbitrary SQL, code, tools, URLs, tenant IDs, and prompt instructions cannot become executable operations.

## ADR-011 — Use bounded durable jobs in PostgreSQL

**Status:** Accepted

Long-running operations enqueue transactionally with their resource state. Workers claim rows through PostgreSQL locks and leases, heartbeat, retry idempotent stages, and recover stale claims. This avoids unreliable in-process background tasks and defers a separate broker until throughput evidence requires it.

## ADR-012 — Stage, preview, and revalidate CSV imports

**Status:** Accepted

Stream bounded UTF-8 CSV to private storage, validate exact templates/types/references/duplicates, persist a safe preview/error summary, and require explicit confirmation. The worker verifies the digest and validates again before an all-or-nothing business commit. CSV exports neutralize spreadsheet formulas.

## ADR-013 — Use a private mounted-filesystem adapter

**Status:** Accepted for the verified topology

The implemented adapter uses opaque keys beneath a contained private root shared by API and worker. It is sufficient for local/Compose verification and hosts with a persistent private volume. A remote object-store adapter is explicit future work and cannot be enabled by configuration alone.

## ADR-014 — Use isolated one-click demo organizations

**Status:** Accepted

Each demo request creates a new user, organization, Owner membership, subscription, seed revision, and opaque session. Server-side demo policy restricts external/destructive/payment behavior, and worker cleanup expires the workspace. No shared privileged password is published.

## ADR-015 — Use a no-charge billing service

**Status:** Accepted

Implement plan catalog, subscription, usage, demonstration invoices, and simulated upgrade/management intents without an external provider. Owner authorization, allowlisted plans, idempotency, and audit history remain realistic while the code is incapable of creating a charge or checkout.

Reserved provider columns/enum space make a future migration possible but do not constitute a payment integration.

## ADR-016 — Use consistent API envelopes and problem details

**Status:** Accepted

Version product APIs under `/api/v1`, return data/collection envelopes, use stable English RFC 9457-style problem documents, propagate request IDs, and expose ETag/idempotency headers. Clients do not depend on stack traces or provider-specific payloads.

## ADR-017 — Use explicit release gates

**Status:** Accepted

Formatting, lint, strict types, unit/integration tests, PostgreSQL migrations, production builds, English/encoding audit, secret audit, accessibility/console browser checks, Docker image builds, and integrated health checks are release criteria. A public deployment is not claimed until HTTPS-domain smoke tests pass.

## Deferred choices

These are intentionally absent from the release candidate:

- public hosting vendor and domain selection;
- PostgreSQL row-level security;
- remote object storage;
- transactional email transport;
- external payment provider;
- external queue/broker;
- PDF reporting;
- real-time warehouse/event ingestion;
- multi-currency conversion;
- enterprise SSO/SCIM/custom roles;
- production error tracking and product analytics.

Each deferred capability requires its own implementation, tests, security/operational review, and an ADR before it appears in visible product promises.

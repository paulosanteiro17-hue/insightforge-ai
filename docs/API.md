# InsightForge AI API Reference

## Contract status

This document describes the implemented FastAPI v1 surface. The generated OpenAPI document at `/api/v1/openapi.json` is authoritative for field-level schemas.

- Local API base: `http://localhost:8000/api/v1`
- Browser base through Next.js: `/api/v1`
- Development Swagger UI: `http://localhost:8000/api/docs`

## Conventions

- JSON fields, enum values, and query parameters use `snake_case`.
- Identifiers are opaque UUIDs.
- Timestamps are RFC 3339 UTC values; calendar dates use `YYYY-MM-DD`.
- Stored money uses PostgreSQL fixed precision. API money fields use integer minor units or explicit decimal strings according to the schema.
- Collection responses contain `data` plus pagination/filter metadata.
- Single-resource responses contain `{ "data": ... }`.
- Errors use `application/problem+json` with `title`, `detail`, `status`, stable `code`, and `request_id`.
- Authenticated and tenant data is private/no-store. Public plan metadata is cacheable.

## Authentication and unsafe requests

Authentication uses an opaque server-side session cookie. The browser never receives an access token. Unsafe requests (`POST`, `PATCH`, and `DELETE`) require a matching `X-CSRF-Token`; the client obtains one from `GET /auth/csrf-token`. Origin checks are also enforced.

Most organization-owned routes require `X-Organization-ID`. The API validates that the current user belongs to that organization and has the route's required permission. Cross-tenant identifiers return the same concealed not-found response as absent identifiers.

Mutation routes that can be retried safely require or accept a UUID `Idempotency-Key`, as declared by OpenAPI. Versioned customer/product/order changes use `If-Match` and return `ETag` values.

## Implemented endpoints

### Health

| Method | Path              | Access | Purpose                          |
| ------ | ----------------- | ------ | -------------------------------- |
| `GET`  | `/health/live`    | Public | Process liveness                 |
| `GET`  | `/health/ready`   | Public | Database and migration readiness |
| `GET`  | `/health/version` | Public | Safe build metadata              |

Health routes are outside `/api/v1`.

### Authentication

| Method | Path                            | Access               | Purpose                                                                   |
| ------ | ------------------------------- | -------------------- | ------------------------------------------------------------------------- |
| `GET`  | `/auth/csrf-token`              | Public/session-aware | Issue or rotate the appropriate CSRF token                                |
| `POST` | `/auth/register`                | Public + CSRF        | Create an account and session                                             |
| `POST` | `/auth/login`                   | Public + CSRF        | Create a session with generic credential errors                           |
| `POST` | `/auth/demo-session`            | Public + CSRF        | Create a rate-limited isolated demo organization/session                  |
| `GET`  | `/auth/session`                 | Session              | Return the current user, session metadata, and memberships                |
| `POST` | `/auth/logout`                  | Session + CSRF       | Revoke the current session and clear cookies                              |
| `POST` | `/auth/password-reset-requests` | Public + CSRF        | Create a short-lived one-time recovery token and return a generic message |
| `POST` | `/auth/password-resets`         | Public + CSRF        | Consume a recovery token, set a new password, and revoke active sessions  |

Recovery requests return `202` with the same message for known and unknown accounts. Development and testing may include a local `recovery_path` for credential-free evaluation. Hosted environments return no token or path; an email transport must be added before enabling public recovery delivery.

### Organizations and users

| Method                   | Path                                                       | Purpose                                                         |
| ------------------------ | ---------------------------------------------------------- | --------------------------------------------------------------- |
| `GET`, `POST`            | `/organizations`                                           | List memberships or create an organization                      |
| `GET`, `PATCH`, `DELETE` | `/organizations/current`                                   | Read/update the active organization or request allowed deletion |
| `POST`                   | `/organizations/current/onboarding/complete`               | Finish onboarding after demo seed or import data exists         |
| `POST`                   | `/organizations/current/demo-data-jobs`                    | Enqueue deterministic demo data                                 |
| `GET`                    | `/organizations/current/demo-data-jobs/{job_id}`           | Poll seed status                                                |
| `GET`                    | `/organizations/current/usage`                             | Return plan usage                                               |
| `GET`, `DELETE`          | `/organizations/current/deletion`                          | Read or cancel scheduled deletion                               |
| `POST`                   | `/organizations/current/data-exports`                      | Enqueue an authorized data export                               |
| `GET`                    | `/organizations/current/data-exports/{export_id}`          | Poll export status                                              |
| `GET`                    | `/organizations/current/data-exports/{export_id}/download` | Download an authorized ready export                             |
| `GET`, `PATCH`           | `/users/me`                                                | Read/update the current profile                                 |
| `GET`, `PATCH`           | `/users/me/preferences`                                    | Read/update notification/display preferences                    |
| `PATCH`                  | `/users/me/password`                                       | Change password after current-password verification             |

### Commerce resources

| Method                   | Path                               | Purpose                                                           |
| ------------------------ | ---------------------------------- | ----------------------------------------------------------------- |
| `GET`, `POST`            | `/customers`                       | Search/filter/page or create customers                            |
| `GET`, `PATCH`, `DELETE` | `/customers/{customer_id}`         | Read/update/soft-delete a customer                                |
| `GET`                    | `/customers/{customer_id}/metrics` | Customer lifetime and recent metrics                              |
| `GET`                    | `/customers/{customer_id}/orders`  | Tenant-scoped customer order history                              |
| `GET`, `POST`            | `/products`                        | Search/filter/page or create products                             |
| `GET`, `PATCH`, `DELETE` | `/products/{product_id}`           | Read/update/archive a product                                     |
| `GET`                    | `/products/{product_id}/metrics`   | Product revenue and unit trends                                   |
| `GET`, `POST`            | `/orders`                          | Search/filter/page or create orders with server-calculated totals |
| `GET`, `PATCH`           | `/orders/{order_id}`               | Read/update an order under transition rules                       |
| `POST`                   | `/orders/{order_id}/cancel`        | Apply a permitted cancellation                                    |
| `POST`                   | `/orders/{order_id}/refund`        | Apply a permitted full refund                                     |

Lists use bounded pagination and explicit allowlisted filters/sorts. Order totals are calculated by the service; clients cannot submit arbitrary final totals.

### Analytics

| Method | Path                             |
| ------ | -------------------------------- |
| `GET`  | `/analytics/overview`            |
| `GET`  | `/analytics/revenue`             |
| `GET`  | `/analytics/sales`               |
| `GET`  | `/analytics/customers`           |
| `GET`  | `/analytics/products`            |
| `GET`  | `/analytics/orders`              |
| `GET`  | `/analytics/mrr`                 |
| `GET`  | `/analytics/categories`          |
| `GET`  | `/analytics/order-statuses`      |
| `GET`  | `/analytics/acquisition`         |
| `GET`  | `/analytics/recent-transactions` |
| `GET`  | `/analytics/filter-options`      |

Analytics accepts validated presets (`7d`, `30d`, `90d`, `year_to_date`) or a bounded custom range. Responses report effective date/time-zone boundaries, comparison context, metric version, and source revision. Eligible-order and refund semantics live in one canonical analytics engine.

### Intelligence

| Method | Path                                       | Purpose                                                |
| ------ | ------------------------------------------ | ------------------------------------------------------ |
| `GET`  | `/insights`                                | List active grounded insights                          |
| `POST` | `/insights/generation-jobs`                | Enqueue insight regeneration                           |
| `GET`  | `/insights/generation-jobs/{job_id}`       | Poll insight job state                                 |
| `GET`  | `/insights/{insight_id}`                   | Read one tenant-scoped insight                         |
| `GET`  | `/weekly-summary/current`                  | Read the persisted current weekly summary              |
| `POST` | `/weekly-summary/generation-jobs`          | Enqueue summary regeneration                           |
| `GET`  | `/weekly-summary/generation-jobs/{job_id}` | Poll summary job state                                 |
| `GET`  | `/ask-data/capabilities`                   | Return supported intents and example questions         |
| `POST` | `/ask-data/answers`                        | Answer a controlled analytics question                 |
| `GET`  | `/ask-data/history`                        | Return the current user's tenant-scoped answer history |

Ask Your Data maps questions to allowlisted analytical intents and typed parameters. It never executes model-authored SQL. Answers carry status, applied range, citations/supporting metrics, confidence where applicable, and follow-up prompts. Suspicious or unsupported input receives a controlled response.

### Reports

| Method        | Path                            | Purpose                                                    |
| ------------- | ------------------------------- | ---------------------------------------------------------- |
| `GET`         | `/reports/templates`            | List implemented report definitions and formats            |
| `GET`, `POST` | `/reports`                      | List generated reports or enqueue a new report             |
| `GET`         | `/reports/{report_id}`          | Poll/read report state                                     |
| `GET`         | `/reports/{report_id}/download` | Stream a ready, unexpired artifact after permission checks |

CSV output uses stable English headers and neutralizes spreadsheet-formula prefixes. JSON and CSV artifacts are private, revisioned, and retention-bound.

### Imports

| Method        | Path                           | Purpose                                                      |
| ------------- | ------------------------------ | ------------------------------------------------------------ |
| `GET`, `POST` | `/imports`                     | List imports or stage an uploaded customer/product/order CSV |
| `GET`         | `/imports/templates/{kind}`    | Download the exact English template                          |
| `GET`         | `/imports/{import_id}`         | Read validation/import state                                 |
| `GET`         | `/imports/{import_id}/preview` | Read the bounded sanitized preview                           |
| `GET`         | `/imports/{import_id}/errors`  | Page through coded validation errors                         |
| `POST`        | `/imports/{import_id}/commit`  | Explicitly enqueue a validated import                        |
| `POST`        | `/imports/{import_id}/cancel`  | Cancel a cancellable staged import                           |

Uploads are streamed to private storage, capped by bytes/rows/fields/error count, hashed, validated before preview, revalidated by the worker before commit, and applied transactionally.

### Team

| Method            | Path                                       | Purpose                                               |
| ----------------- | ------------------------------------------ | ----------------------------------------------------- |
| `GET`             | `/team/members`                            | List active organization members                      |
| `PATCH`, `DELETE` | `/team/members/{member_id}`                | Change an allowed role or remove a member             |
| `GET`, `POST`     | `/team/invitations`                        | List or create invitations                            |
| `POST`            | `/team/invitations/{invitation_id}/resend` | Rotate and reissue a pending invitation token         |
| `DELETE`          | `/team/invitations/{invitation_id}`        | Revoke an invitation                                  |
| `GET`, `POST`     | `/team/invitations/accept/{token}`         | Public preview or authenticated single-use acceptance |
| `POST`            | `/team/leave`                              | Leave when owner constraints allow it                 |

Invitation tokens are random, hashed at rest, short-lived, and single-use. The last owner cannot leave, be removed, or be demoted.

### Billing

| Method | Path                       | Purpose                                                 |
| ------ | -------------------------- | ------------------------------------------------------- |
| `GET`  | `/billing/plans`           | Public Free/Pro/Business metadata and limits            |
| `GET`  | `/billing/subscription`    | Owner-only normalized subscription and usage            |
| `GET`  | `/billing/invoices`        | Owner-only demonstration invoice records                |
| `POST` | `/billing/upgrade-intents` | Idempotently apply an allowlisted no-charge plan change |
| `POST` | `/billing/portal-intents`  | Return the in-application billing destination           |

Billing is deliberately simulated. These routes cannot create a checkout, collect card data, call a payment network, or return an external payment URL.

## Background processing

Long-running commands enqueue a `background_jobs` row in the same transaction as their resource state change. Workers claim jobs with PostgreSQL row locks and time-bounded leases, renew active claims, recover stale work, and apply bounded retries to idempotent handlers. Each job reloads current tenant and requester permission before a final commit or external AI call.

## Error and safety behavior

- `400`: invalid state/token/idempotency contract.
- `401`: authentication required, invalid credentials, or expired/revoked session.
- `403`: authenticated but missing an organization permission.
- `404`: absent or concealed tenant-owned resource.
- `409`: duplicate resource, replay in progress, or invalid state transition.
- `412`: stale `If-Match` version.
- `413`: upload too large.
- `422`: schema or domain validation failure.
- `429`: bounded rate limit with `Retry-After`.
- `503`: dependency/readiness/provider unavailable with a safe message.

Errors never include SQL, stack traces, tokens, cookies, storage keys, provider payloads, or another tenant's existence.

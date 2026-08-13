# InsightForge AI Security

## Scope

This document records implemented controls, assumptions, and residual risks for the release-candidate repository. It is not a claim of third-party certification or penetration testing.

Protected assets include account/session credentials, organization business records, private CSV/report artifacts, tenant boundaries, metric integrity, AI aggregate context, audit records, and deployment secrets.

## Authentication

- Passwords use Argon2id through `argon2-cffi`; hashes include their work parameters and can be upgraded after login.
- Unknown-user login performs a dummy hash verification to reduce account-timing disclosure.
- Credential errors are generic.
- Session tokens contain at least 256 bits of randomness. Only SHA-256 digests are stored.
- Sessions have idle/absolute expiry, revocation, safe client metadata digests, and server-side current-state checks.
- The default session idle timeout is 30 minutes. Absolute expiry remains independently bounded and configurable.
- Production startup rejects insecure session-cookie mode. The production session cookie is Secure, HttpOnly, SameSite Lax, Path `/`, and uses a `__Host-` name. CSRF and demo-scope cookies also use host-prefixed names in secure deployments.
- Login, registration, demo creation, password change/recovery, invitation, Ask Your Data, insight generation, and report generation have bounded application rate limits. Public infrastructure still requires trusted edge limits.

## Password recovery

- Requests return the same public message for existing and unknown accounts.
- Tokens are random, purpose-bound, short-lived, single-use, and stored only as hashes.
- A new request consumes prior active recovery tokens for that account.
- Successful recovery changes the password hash and revokes every active session.
- Development/testing may return a local recovery path to exercise the flow without email credentials. Hosted environments return no token/path; a reviewed email transport is required for public delivery.

## CSRF, origins, and browser security

- Unsafe cookie-authenticated requests require double-submit CSRF.
- Authenticated CSRF tokens are random and digest-bound to the session.
- Pre-authentication CSRF tokens are HMAC-signed, time-bounded, and tied to the safe demo browser-scope workflow.
- Unsafe requests validate exact allowed origins. Origins cannot contain credentials, wildcards, paths, queries, or fragments; CSRF origins must also be in the CORS allowlist; staging and production require HTTPS.
- Trusted-host middleware restricts accepted explicit hosts. Server-side web requests use configured upstream/public origins and never derive the upstream from a request Host header.
- Next.js sends Content Security Policy, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy: no-referrer`, a restrictive Permissions Policy, and HSTS when the configured public origin is HTTPS. The API sends the corresponding baseline and enables HSTS outside local development.
- Token-bearing recovery/invitation pages do not load third-party analytics in this repository.

## Tenant isolation and permissions

- The active organization comes from authenticated membership plus `X-Organization-ID`, never from an AI prompt or arbitrary payload field.
- Route dependencies establish `TenantContext` and enforce Owner/Admin/Member permissions.
- Services enforce operation-specific rules, including final-owner protection and demo restrictions.
- Repositories scope tenant reads/writes by organization.
- Tenant-owned child records store `organization_id`; composite constraints prevent links to another tenant's parent rows.
- Organization-scoped unique constraints avoid cross-tenant uniqueness leaks.
- Cross-tenant identifiers use concealed not-found behavior.
- Background jobs persist trusted organization/requester IDs and revalidate membership/permission before final work.
- Frontend cache/query keys include organization context; changing organizations cannot authorize data.

PostgreSQL row-level security is not implemented or claimed. The application and constraint layers are the active controls.

## Demo isolation

- One-click access creates a new user, organization, membership, subscription, seed revision, and opaque session; no reusable Owner password is published.
- Creation is protected by CSRF, browser/global rate limits, and idempotency.
- The demo session is marked server-side and may access only its own demo organization.
- Demo policy blocks unsafe external/payment/destructive behavior even when the membership role is Owner.
- Demo organizations expire and are eligible for worker cleanup.
- Billing transitions are simulated and cannot contact a payment network or collect payment information.

## CSV uploads and private artifacts

- A global 12 MiB request-body cap runs before framework parsing and covers declared and streamed bodies. Configuration requires this cap to exceed the endpoint upload cap.
- Upload size defaults to 10 MiB and row count to 50,000, with caps for columns, fields, preview rows, and reported errors.
- Input is treated as inert UTF-8 CSV. Filename and MIME type are not trusted.
- Exact versioned headers, data types, enums, dates, references, and duplicate rules are validated.
- Files stream to a private root through server-generated opaque keys; resolved-path containment prevents traversal.
- Private artifacts live outside public web roots and use restrictive local permissions.
- A SHA-256 digest detects replacement between validation and commit.
- Previews/errors expose bounded normalized content and safe excerpts, never object keys or direct filesystem paths.
- Import confirmation rechecks status/revision and the worker revalidates the retained file.
- Business writes commit transactionally; unexpected failure rolls them back.
- Every preview/download rechecks current tenant permission.
- Retention and cleanup jobs expire imports, reports, and exports.
- CSV exports neutralize dangerous leading formula characters and use attachment disposition.

The included adapter uses a private local/mounted filesystem. A hosted deployment must supply persistent private storage. Remote object storage is not implemented and must not be assumed from configuration alone.

## AI safety

- Canonical analytics computes numbers before explanation.
- Deterministic AI is the default, requires no provider key, and remains usable during external-provider failure.
- The optional OpenAI adapter receives bounded aggregate findings, not raw rows, database access, session state, or tenant-selection authority.
- Provider output is schema-validated, size-bounded, and rendered as text by React.
- Provider/model/prompt version and generation mode are persisted for provenance.
- Ask Your Data maps questions to allowlisted analytical intents and typed parameters; no model-authored SQL, code, URLs, or arbitrary tools execute.
- Suspicious prompts and unsupported requests receive controlled statuses.
- Answers cite the supporting aggregate metrics and applied range.
- Prompts/provider bodies and unnecessary customer data are excluded from general logs.

## Business and report integrity

- Stored money uses fixed precision; API/client values do not control final order totals.
- Order totals and status transitions are calculated/validated server-side.
- `ETag` and `If-Match` prevent silent overwrites of versioned resources.
- Reports are generated from allowlisted definitions and source revisions.
- Artifact access requires both current permission and ready/unexpired state.
- Idempotency records prevent duplicate retries for demo creation, orders, jobs, billing intents, and other replay-sensitive commands.

## Billing safety

- The implementation is a local no-charge service with fixed plan identifiers and prices.
- Only Owners can read/manage subscription state.
- Clients cannot submit an arbitrary price or amount.
- Simulated transitions are idempotent and audited.
- There is no payment SDK, checkout URL, payment-method form, card-data store, provider portal, or payment webhook endpoint.
- Reserved provider schema fields are not evidence of an external integration.

## Secrets and logs

- Secrets enter through environment variables or a deployment secret manager. `.env.example` contains local-only non-secret placeholders.
- Staging/production startup validates secure cookies, non-development CSRF signing material, exact origins/hosts, provider choice, and conditional OpenAI credentials.
- Structured logs carry request IDs, route templates, status, duration, safe codes, and job identifiers.
- Logs exclude/rewrite passwords, cookies, CSRF/session/action/invitation tokens, authorization headers, API keys, database credentials, raw uploads, private paths, and AI prompts.
- Audit rows store actor, organization, action, resource, request ID, timestamp, and bounded safe metadata.
- `scripts/audit-secrets.mjs` scans repository text for credential-like content before release.

## Dependency and quality gates

- npm and uv lockfiles are committed.
- CI uses `npm ci` and `uv sync --locked`; third-party GitHub Actions are pinned to full commit SHAs, and Dependabot covers npm, uv, actions, and Docker inputs.
- npm audit, pip-audit, Bandit, ESLint, Ruff security rules, strict mypy, TypeScript, tests, migrations, builds, content/encoding audit, secret audit, and integrated containers are release gates.
- Runtime images remove build-only package managers. Compose application services use read-only root filesystems, no Linux capabilities, no-new-privileges, bounded temporary filesystems, and loopback-only published ports by default.
- Playwright includes automated axe WCAG A/AA checks and representative console/page-error checks.
- The August 13, 2026 internal review recorded zero known npm/Python dependency vulnerabilities, zero Bandit/Semgrep findings, zero fixable high/critical runtime-image findings, and zero OWASP ZAP passive failures. See [Security audit](SECURITY_AUDIT.md) for scope, remediations, evidence, and warning disposition.

## Residual risk and hosted-release requirements

- No third-party penetration test or independent security audit has been performed; the recorded review is an internal engineering audit.
- The static-compatible CSP currently permits inline framework scripts. Keep third-party scripts absent and adopt request nonces if the script trust boundary expands.
- The in-process rate limiter is per API process; public deployment requires trusted edge/global abuse controls.
- PostgreSQL RLS is absent; repository/policy/constraint discipline must remain covered by adversarial tenant tests.
- Transactional email is absent; public recovery/invitation delivery needs a reviewed provider, redaction, retry, and abuse design.
- Remote object storage is absent; public infrastructure must provide persistent private storage or a newly tested adapter.
- The OpenAI adapter requires provider-specific privacy, retention, region, cost, model, and incident review before real customer data.
- Demo data is fictional, but user-created workspaces can contain personal/business data; privacy, retention, backup, and deletion policies need legal/operational approval before production use.
- Backup restore, TLS/cookie/proxy behavior, observability, incident response, and rollback must be verified on the final host.

Critical/high security findings block public release. Lower-severity accepted risks must be documented with owner and remediation.

## Reporting a security issue

Do not open a public issue containing a secret, token, personal data, exploit payload, or tenant-isolation proof. Contact the repository owner privately with the affected revision, route/component, reproduction steps using fictional data, and observed impact. Revoke exposed credentials before sharing supporting logs.

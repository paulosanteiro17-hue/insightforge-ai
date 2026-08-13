# InsightForge AI Route Map

## Routing rules

- Public marketing, authentication, onboarding, and product routes use separate Next.js layouts.
- Product URLs include the organization slug for navigation; FastAPI resolves access from the authenticated membership and organization ID.
- Private product routes use no-index metadata and never expose cached tenant data publicly.
- Range, search, filters, sorting, and pagination live in validated URL parameters where they affect the visible result.
- Every visible navigation destination and primary action is implemented.

## Public marketing

| Route      | Purpose                                                                                                                      |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `/`        | Product story, dashboard preview, AI safety explanation, workflow, pricing preview, demo/sign-up calls to action, and footer |
| `/pricing` | Free, Pro, and Business presentation with explicit no-charge portfolio billing                                               |
| `/privacy` | Portfolio privacy notice, data categories, retention, AI provider behavior, and contact guidance                             |
| `/terms`   | Demo terms, acceptable use, billing limitations, and warranty/license context                                                |

The marketing shell uses a desktop header and accessible mobile menu. Content is English and avoids unverified customer, uptime, or performance claims.

## Authentication and invitation

| Route                        | Purpose                                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `/login`                     | Email/password sign-in, Forgot Password link, Sign Up link, and one-click isolated Demo Owner entry         |
| `/signup`                    | Create an account with display name, email, strong password, and terms acknowledgment                       |
| `/forgot-password`           | Submit an email and always receive the same generic recovery message                                        |
| `/reset-password?token=...`  | Set/confirm a new password with a one-time recovery token, revoke old sessions, and return to sign-in       |
| `/accept-invitation/[token]` | Preview the organization/role safely, sign in when necessary, and explicitly accept a single-use invitation |

Development/testing recovery responses may expose a local continuation link so the workflow remains testable without email credentials. Hosted environments require an email transport and never return the token to the requester.

## Organization onboarding

| Route                                | Purpose                                                                                               |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `/onboarding`                        | Create the first organization with name, time zone, currency, and optional industry                   |
| `/app/[organizationSlug]/onboarding` | Choose deterministic demo data or CSV import, review the result, and complete organization onboarding |

Onboarding choices persist for the session and remain resumable. Completion is accepted only after the selected demo seed or CSV import produced records.

## Product workspace

| Route                                            | Purpose                                                                                                          | Primary URL state                         |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `/app`                                           | Resolve the current session to onboarding or an authorized organization                                          |
| `/app/[organizationSlug]`                        | Redirect to the organization overview                                                                            |
| `/app/[organizationSlug]/overview`               | KPI cards, revenue/category/acquisition/order charts, products, Weekly Business Summary, and recent transactions | `range`                                   |
| `/app/[organizationSlug]/analytics`              | Detailed revenue/order/customer/product performance and comparisons                                              | `range`                                   |
| `/app/[organizationSlug]/sales`                  | Searchable/filterable/sortable paginated orders                                                                  | `q`, `status`, `sort`, `page`             |
| `/app/[organizationSlug]/sales/orders/[orderId]` | Order/customer/items/totals/status detail and allowed transitions                                                | none                                      |
| `/app/[organizationSlug]/customers`              | Search, status/segment filter, sorting, pagination, and customer creation for allowed roles                      | `q`, `status`, `segment`, `sort`, `page`  |
| `/app/[organizationSlug]/customers/[customerId]` | Customer identity, lifetime metrics, and recent orders                                                           | none                                      |
| `/app/[organizationSlug]/products`               | Search, category/status filter, sorting, pagination, and product creation for allowed roles                      | `q`, `category`, `status`, `sort`, `page` |
| `/app/[organizationSlug]/products/[productId]`   | Catalog information, revenue/unit trends, and product metrics                                                    | none                                      |
| `/app/[organizationSlug]/ai-insights`            | Grounded insight cards, filters, date range, provenance, and regeneration                                        | `range`, `q`, `category`, `severity`      |
| `/app/[organizationSlug]/ask-your-data`          | Controlled questions, cited answers, safety states, examples, and history                                        | `range`                                   |
| `/app/[organizationSlug]/reports`                | Report templates, editable request name/format, filters, history, polling, and download                          | `range`, `q`, `type`, `status`            |
| `/app/[organizationSlug]/data-sources`           | CSV templates, staged upload, validation preview/errors, confirmation, and import history                        | none                                      |
| `/app/[organizationSlug]/team`                   | Members, permissions, invitations, one-time links, roles, removal, revocation, and owner constraints             | none                                      |
| `/app/[organizationSlug]/billing`                | Plans, current no-charge subscription, usage, simulated plan changes, and demonstration invoice records          | none                                      |
| `/app/[organizationSlug]/settings`               | Profile/preferences, organization configuration, audit/data export, deletion state, and demo restrictions        | local section state                       |

## Access model

- Member: view business data, analytics, insights, reports, and controlled Ask Your Data answers.
- Admin: Member capabilities plus business data/import administration and Member invitation/removal where allowed.
- Owner: Admin capabilities plus role administration, billing, data export, and destructive organization controls.
- Demo Owner: Owner presentation with server-enforced restrictions on external/destructive/payment behavior and all non-demo organizations.

UI gating improves clarity but does not provide security. The API rechecks every permission.

## Shared states and responsive behavior

Product pages provide deliberate loading skeletons, empty states, retryable error states, permission-safe not-found behavior, and mutation status announcements. Desktop tables transform into mobile cards where horizontal density would harm readability. Product navigation becomes a modal dialog on compact viewports.

Interactive elements have keyboard-visible focus, semantic labels, minimum practical touch sizes, and no hover-only critical action. Range controls expose `aria-pressed`; dialogs expose names and focus boundaries; status updates use live regions where appropriate.

## Critical journeys

1. Landing page → Login → isolated Demo Owner → Overview → change range.
2. Login → Forgot Password → local recovery link → set password → sign in again.
3. Overview → Analytics → Sales → filter → Order detail.
4. Customers → filter → Customer detail → Products → Product detail.
5. AI Insights → filter/regenerate → Ask Your Data → grounded answer → safety-blocked prompt.
6. Reports → generate → worker completion → authorized download.
7. Data Sources → upload CSV → validation preview → explicit commit → completed history.
8. Onboarding → configure organization → choose demo or import → review → complete.
9. Team → create invitation → copy single-use link → public preview → accept/revoke.
10. Billing → inspect usage → simulate no-charge plan change → view demonstration records.
11. Settings → update profile/preferences/organization → request data export → inspect deletion policy.
12. User menu → sign out → protected route returns to login.

These journeys are represented in Playwright mock tests; the live production-stack test covers demo creation, worker-generated insights, worker-generated report, and artifact download.

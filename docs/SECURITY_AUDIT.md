# InsightForge AI Security Audit

## Audit status

An internal source, dependency, container, configuration, and passive HTTP security review was completed on August 13, 2026. All confirmed findings identified during this review were remediated and regression-tested. The final automated scans report no known application dependency vulnerability, no blocking static-analysis finding, no exposed repository secret, no fixable high/critical runtime-image vulnerability, and no passive HTTP failure.

A publication follow-up on August 14, 2026 remediated a newly surfaced GitHub advisory affecting the development test runner and added grouped dependency-update automation.

This is an engineering security review, not an independent penetration test or certification. Hosted infrastructure, TLS termination, managed-database permissions, backup restoration, edge rate limiting, and incident operations remain deployment-specific gates.

## Scope and method

The review covered:

- authentication, session, CSRF, recovery, invitation, and demo-session flows;
- organization selection, permissions, tenant-scoped repositories, composite constraints, and background jobs;
- CSV parsing, private artifact paths, report/export downloads, and spreadsheet-formula neutralization;
- AI provider boundaries, aggregate-only context, schema validation, and Ask Your Data intent routing;
- Next.js-to-FastAPI proxy trust, origins, hosts, cookies, response headers, request limits, and error handling;
- npm and Python dependency graphs, Docker runtime layers, Compose isolation, CI action pinning, and secret handling;
- full source scans with Bandit and Semgrep, runtime-image and repository scans with Trivy, and a passive OWASP ZAP baseline crawl.

The review also exercised the complete backend suite against a newly migrated PostgreSQL database, browser journeys, production builds, and the hardened Compose stack.

## Remediated findings

| ID     | Severity | Finding                                                                                                                                                                                        | Resolution                                                                                                                                                                                     |
| ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SEC-01 | High     | Runtime images retained build/package-manager components with fixable high/critical transitive advisories.                                                                                     | The API runtime now removes Python packaging tools, and the web runtime removes the global npm toolchain. Rebuilt images contain zero fixable high/critical findings in the final Trivy scan.  |
| SEC-02 | Medium   | A missing web upstream setting could fall back to request-derived host/protocol values, creating a host-header trust and server-side request-routing risk.                                     | API and public web origins now come only from validated, explicit configuration with safe local defaults. Request headers never select the internal upstream.                                  |
| SEC-03 | Medium   | General HTTP request bodies were not capped before framework parsing; endpoint upload limits alone did not cover every route or chunked body.                                                  | A pure ASGI limit rejects invalid, declared oversized, and streamed oversized bodies with bounded problem responses. The request cap must remain greater than the CSV upload cap.              |
| SEC-04 | Medium   | Deployment trust settings accepted more ambiguous values than necessary, and the default session idle lifetime was excessive.                                                                  | Origins must be unique exact HTTP(S) origins, CSRF origins must be a CORS subset, hosts must be explicit, hosted origins must use HTTPS, and the default idle timeout is 30 minutes.           |
| SEC-05 | Medium   | Application containers used writable root filesystems and retained default Linux capabilities. Published local ports listened on every interface.                                              | API, worker, migration, and web containers are read-only, drop all capabilities, prohibit privilege escalation, use bounded temporary filesystems, and bind host ports to loopback by default. |
| SEC-06 | Low      | CI actions used mutable major tags and dependency security checks were not explicit gates.                                                                                                     | Third-party actions are pinned to full commit SHAs; npm, pip-audit, and Bandit gates plus Dependabot coverage were added.                                                                      |
| SEC-07 | Low      | Auxiliary cookie names did not receive the same production host-prefix protection as the session cookie, and authenticated cache protection did not account for every cookie-setting response. | Secure deployments use `__Host-` names for session, CSRF, and demo-scope cookies. Cookie-setting responses are private and non-storable.                                                       |
| SEC-08 | Medium   | GitHub's advisory database identified vulnerable temporary-directory handling in the development-only `pytest 8.4.2` lockfile entry after publication.                                         | `pytest` was upgraded to 9.1.1 and `pytest-asyncio` to 1.4.0. The patched toolchain passed the backend regression suite and remains covered by CI and Dependabot.                              |

## Verification evidence

| Gate                                                  | Result                                                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Backend tests on a fresh migrated PostgreSQL database | 154 passed                                                                                       |
| Frontend unit/component tests                         | 30 passed                                                                                        |
| Mock browser journeys                                 | 14 passed; 3 explicitly optional capture/live tests skipped                                      |
| Live hardened-stack journey                           | 1 passed, including demo creation, worker AI insight, report generation, and authorized download |
| npm audit                                             | 0 known vulnerabilities                                                                          |
| pip-audit on the locked production graph              | 0 known vulnerabilities                                                                          |
| Bandit                                                | 0 medium/high findings and no suppressed lines                                                   |
| Semgrep default ruleset                               | 452 rules over 232 files, 0 findings                                                             |
| Trivy final API/web runtime images                    | 0 fixable high/critical vulnerabilities                                                          |
| Trivy repository configuration and secret scan        | 0 findings                                                                                       |
| OWASP ZAP passive baseline                            | 59 passed, 0 failed, 8 reviewed warnings                                                         |
| ESLint, Ruff, strict mypy, TypeScript, and formatting | Passed                                                                                           |
| Next.js production build and Python wheel/sdist       | Passed                                                                                           |
| Hardened Compose services and health checks           | Passed                                                                                           |

The ZAP warnings were reviewed individually. Scanner-injected credential-like query parameters are not generated by the application; authentication submits JSON through unsafe POST requests. Authentication redirects, modern-app detection, and non-storable protected content are expected. A bodyless framework redirect omitted `Content-Type`, which is not a content-sniffing exposure. Cross-Origin-Embedder-Policy is optional for this application and would impose resource compatibility constraints without addressing an identified exploit.

The production CSP retains `unsafe-inline` in `script-src` for Next.js static rendering compatibility. The application has no scanner-detected dangerous JavaScript functions, no third-party script source, and no raw HTML rendering sink. A nonce-based dynamic CSP is the preferred future change if external scripts or additional injection surfaces are introduced.

## Residual risks and release gates

- Rate limiting is process-local. A public deployment requires a trusted edge or shared global limiter.
- PostgreSQL row-level security is not implemented; application policies, tenant-scoped repositories, constraints, and adversarial tests remain the active controls.
- The filesystem storage adapter requires a private persistent volume shared by API and worker. Remote object storage needs a separately implemented and tested adapter.
- Transactional email is not implemented. Hosted invitation and recovery delivery needs provider, retry, abuse, privacy, and redaction review.
- OpenAI is optional and disabled by default. Enabling it requires provider retention, privacy, region, cost, model, and incident-response approval.
- A public release still requires independent testing appropriate to its risk, HTTPS/proxy validation on the real domains, least-privilege managed database roles, backup/restore evidence, observability, and an incident/rollback exercise.

See [Security](SECURITY.md) for the standing control model and [Deployment](DEPLOYMENT.md) for hosted release gates.

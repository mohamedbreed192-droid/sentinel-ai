# Verification record

Verified on 2026-11-16 in a managed Linux workspace, Python 3.12, Node 22-compatible tooling, system Chromium, Docker 29.9.2. These are observed checks, not claims of production reliability.

| Check | Observed result |
| --- | --- |
| Backend unit/integration suite | **28 passed**; one third-party Starlette TestClient deprecation warning |
| Next.js production build | Passed with strict TypeScript |
| Playwright interaction flow | Passed: navigation, finding search/severity filter, graph impact, explanation, proposed patch display, report download, coverage and import dialog |
| Playwright mobile viewport | Passed at 390 × 844; document width did not exceed viewport |
| Screenshot capture | Overview, findings, digital twin, assistant, mobile; files visually inspected |
| SQLite migration smoke check | Alembic upgrade passed |
| PostgreSQL migration | Alembic upgrade passed against PostgreSQL 17 container |
| Async integration | Real FastAPI + Celery worker + Redis 7 + PostgreSQL 17 completed a public repository import |
| Live import target | `mohamedbreed192-droid/incidentlens`, commit `b74086b4e3f831e83ac053275fd172b8ad20dd8c` |
| Live import result | 31 source modules; 105 Bandit signals and 1 Semgrep signal; dependency scanners correctly not applicable; report export/history/auth checks passed |
| Fixture analysis | 7 actual scanner signals: Bandit 5, Semgrep 2; dependency scans not applicable |
| Credential redaction | Synthetic credential value absent from normalized JSON and Markdown; tested automatically |
| pip-audit adapter probe | Exact-pinned temporary urllib3 1.26.5 fixture produced 18 advisory signals without package installation |
| npm audit adapter probe | Temporary lodash 4.17.20 lockfile produced a dependency finding without package installation |
| Isolated Docker tests | **3 passed**: non-root/read-only/no Docker socket, blocked outbound network, writable ephemeral /tmp |
| Frontend dependency audit | 0 known advisories at verification time |
| Python dependency audit | 6 known advisories in 2 Semgrep-pinned CLI dependencies; documented expiring baseline, **not fixed** |

A signal count includes review items such as assertions in tests and use of subprocess APIs. Overlap between scanners is not deduplicated. These counts do not mean that the imported repository has that many exploitable vulnerabilities.

## Verification limits

The full application Docker Compose build was attempted twice but exceeded the environment's 8 GB filesystem while using Docker's VFS storage driver. The Dockerfiles were reduced, and PostgreSQL/Redis containers plus host-run FastAPI/Celery were verified together instead. The entire production-shaped application container build is **not locally verified**. The GitHub Actions container job provides a separate build/start/sandbox check; consult its actual run result before claiming it passed.

The managed environment uses an outbound TLS inspection CA. Session-only BuildKit secret mounts supplied that CA to package installers; TLS verification stayed enabled. These adaptations and credentials are not included in project source. Standard Dockerfiles retain normal public-registry trust behavior.

Browser checks used the project's headless Playwright runner and real system Chromium, not a shared signed-in browser. Screenshots use real scanner output from synthetic fixtures and do not show a production customer repository. Proposed patches and generated test templates were displayed, not applied or verified. Optional live OpenAI calls and external production hosting were not tested. No draft PR, merge, or application deployment was created.

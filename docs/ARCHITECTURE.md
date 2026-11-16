# Architecture

## Request to report

FastAPI validates a strict HTTPS github.com owner/repository URL and stores a job before publishing its identifier to Redis. Celery reads the job, marks it running, downloads a public commit-pinned archive, runs scanner adapters, builds an import graph, and persists a JSON report. Alembic creates the relational history table. Scanner raw JSON and repository snapshots are temporary; stored findings contain source-free evidence. The frontend proxies a bounded API route set and forwards the bearer token supplied by the owner. It never injects a server-side token into an anonymous request.

The queue admission cap is a best-effort bound of three active jobs in the initial single-owner deployment. Concurrent submissions can race; deploy-wide rate limiting and transactional admission are needed for shared use. PostgreSQL stores jobs, Redis stores task delivery. The DB commit and task publish are not atomic: publish failures mark jobs failed, but a process crash between them can strand a queued job. An outbox, periodic reconciliation, leases, and authenticated retry/cancellation endpoints are future work. Celery late acknowledgements can redeliver: completed jobs short-circuit, but work already in progress is not protected by a distributed lease. API history is bounded to 50 returned records; retention cleanup is operator-owned.

## Adapter boundary

`scanners.scan` wraps each tool independently. Results normalize into stable IDs, rule, scanner, severity, relative file, line, evidence, remediation, and state. Coverage is completed, failed, unavailable, or not_applicable. A parser error marks the adapter failed rather than accepting its output as a clean scan. A global report can still complete with partial coverage; that status is explicit.

Subprocesses run without a shell, in fresh temporary HOME directories, with CPU/address-space/file-descriptor/output limits and process-group timeout termination. An environment allowlist passes only executable discovery, proxy, and CA settings. API keys are not inherited. Output is captured into bounded temporary files rather than application logs. Scanner tools parse repository data but do not execute it. Scanners remain attack surface; worker containers are unprivileged and never mount the Docker socket.

## Digital twin

Python AST imports resolve to local files, including relative imports. JavaScript/TypeScript relative imports resolve to source files and `index.ts`. Edges point from importer to imported module. Selecting a finding computes reverse reachability using a visited set, including cycles: importers may depend on that component. This expresses static coupling, not exploitability or observed runtime service propagation. Third-party packages, aliases, re-exports, dynamic loading, dependency injection and cross-service calls are not modeled. The dashboard renders the first 30 modules to bound the visual; complete graph data stays in the report.

## Assistant

Deterministic explanation is always available. Optional OpenAI calls require an explicit request flag and configured key. Only normalized scanner metadata is sent. No repository source or source evidence goes to a model. The output is a conceptual recommendation, not an applicable LLM patch. Deterministic patch proposals support a very narrow eval(identifier) statement: a zero-context diff adds `import ast` and changes the call. It respects docstrings/future imports and refuses complex expressions. Every patch is explicitly unverified and never applied.

## Deployment choice

The requested Python/PostgreSQL/Redis/Celery stack uses Docker Compose; it cannot run as a Cloudflare Worker-based Sites application. The application and profile are published through GitHub. No Sites project or live deployment is represented as completed. Local verification uses Docker and the project's Playwright test runner. Session proxy CA adjustments used during verification are outside the tracked source.

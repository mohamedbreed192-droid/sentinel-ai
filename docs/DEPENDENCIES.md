# Dependency audit baseline

Audit date: 2026-11-16. `npm audit` reported **0** known vulnerabilities in the frontend lockfile. This is point-in-time advisory coverage, not a security guarantee.

The installed Semgrep 1.185.0 release pins `mcp==1.29.0` and `opentelemetry-api~=1.37.0`. A full `pip-audit` reported six advisories in those two packages:

| Dependency | Advisory | Upstream fixed versions |
| --- | --- | --- |
| mcp 1.29.0 | CVE-2026-59951 | 1.30.0 / 2.2.0 |
| mcp 1.29.0 | CVE-2026-116685 | 1.30.0 / 2.2.0 |
| mcp 1.29.0 | CVE-2026-116684 | 1.30.0 / 2.2.0 |
| mcp 1.29.0 | CVE-2026-116686 | 1.30.0 / 2.2.0 |
| opentelemetry-api 1.37.0 | CVE-2026-114603 | 1.45.1 |
| opentelemetry-api 1.37.0 | CVE-2026-126360 | 1.45.2 |

These are **unresolved**, not fixed by this project. Upgrading them directly violates the installed Semgrep package constraints, so the lockfile preserves a reproducible upstream-supported installation. Semgrep is invoked only as a bounded CLI with local rules, metrics disabled, a temporary HOME, and a restricted environment. The MCP server capability is not launched. This reduces exposure but does not establish non-applicability of every advisory.

CI uploads the full machine-readable audit. A separate policy check tolerates only these exact package/version/advisory tuples, until **2026-12-16**; any new advisory, version change, audit error, or expired exception fails that check. Update the scanner release and remove this baseline when upstream supports fixed dependencies. Do not use this baseline for an internet-facing production deployment.

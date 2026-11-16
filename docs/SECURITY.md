# Security model

## Intended boundary

Single owner, local loopback deployment. All job/history/explanation/report endpoints require a configured bearer token. `/health` and the source-free synthetic `/demo` report are public. The browser does not persist the token. Rotate it by changing `.env` and recreating API services. No credentials belong in Git history. PostgreSQL and Redis have no host-published ports; Compose networking is not tenant isolation. All backend services currently receive the same `.env`; split service credentials and add a secrets manager before production use.

## Repository import

Only strict HTTPS github.com URLs are accepted. Fixed GitHub API/codeload origins are constructed internally; redirects are refused. Public metadata and canonical full name are verified before import. A 40-character commit SHA pins the snapshot. Compressed content is bounded to 20 MB; declared extracted content to 60 MB; individual files to 2 MB; archive entries to 5,000. Absolute paths, traversal, links and device nodes are rejected. Only a supported text-file extension allowlist is materialized. No shell scripts, Git hooks, installers, npm lifecycle scripts, or repository tests execute during analysis.

The parser runs in a worker container with resource restrictions, not a dedicated microVM. Malicious parser inputs and tool vulnerabilities remain possible. Limit egress to GitHub and advisory registries using deployment infrastructure; Compose does not provide domain-level egress rules. Decompression and HTTP imports have time/size limits; upstream rate limits can still make a job fail.

## Secrets

Scanner lines, matched metavariable values and arbitrary issue prose are omitted. Reports use scanner/rule/location evidence. Scanner errors are sanitized rather than persisted verbatim. Optional LLM input is a metadata allowlist. Patch diffs have zero context and only accept identifier-only statements, preventing surrounding credential source from entering a proposal. Filenames and metadata can still disclose repository structure; restrict access appropriately. Imported content is deleted after the job. This does not prove that every conceivable secret-like filename or external tool behavior is filtered.

## Dependency auditing

pip-audit runs only exact `name==version` pins copied into a fresh requirements file with dependency resolution and pip disabled. npm audit receives copied lock metadata, a synthetic manifest, a fresh HOME, no source npmrc, and `--ignore-scripts`. No dependency packages are installed. Both services require outbound registry access. Audit service failure is partial coverage. Repository files may contain unused/transitive manifests; findings are review signals.

## Proposed changes and tests

Patches are displayed only. No file writes, commits, PR creation, merges or deployments are exposed by the analyzer. The separate CLI requires `--enable-untrusted-tests`. Its Docker container is offline, unprivileged, read-only and constrained; no host Docker socket is mounted inside it. Existing pytest configuration and test code remain arbitrary code within that container. Never use this setup as a claim of protection against kernel/container escapes.

## Before public hosting

Add TLS, per-user sign-in, tenant ownership checks, proper secret storage, distributed admission/rate limits, task leases/reconciliation, retention, monitoring and a hardened disposable worker boundary. There is no claim that these production requirements are implemented. Report vulnerabilities privately to the repository owner; do not post credential values in issues.

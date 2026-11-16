"""Scanner adapters return normalized, source-free evidence and explicit coverage."""
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import tempfile

SEVERITY = {"ERROR": "high", "WARNING": "medium", "INFO": "low", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}

def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (100, 100))
    resource.setrlimit(resource.RLIMIT_AS, (3_000_000_000, 3_000_000_000))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8_000_000, 8_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))

def run_json(command: list[str], cwd: Path, accepted=(0, 1)) -> dict:
    # stdout/stderr are bounded files; raw scanner output never reaches reports/logs.
    with tempfile.TemporaryDirectory(prefix="scanner-home-") as scanner_home, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        env = {key: value for key, value in os.environ.items() if key in {"PATH", "LD_LIBRARY_PATH", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY"}}
        env["HOME"] = scanner_home
        env["SEMGREP_SEND_METRICS"] = "off"
        process = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr, env=env, preexec_fn=limits, start_new_session=True)
        try:
            code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError("Scanner timed out") from None
        if code not in accepted:
            raise RuntimeError(f"Scanner exited with code {code}")
        stdout.seek(0)
        return json.loads(stdout.read(8_000_001))

def safe_path(raw: str, root: Path) -> str:
    candidate = Path(raw)
    try:
        return str(candidate.resolve().relative_to(root.resolve())) if candidate.is_absolute() else str(candidate.relative_to("."))
    except ValueError:
        return "repository"

def finding(scanner, rule, severity, file, line, title, remediation):
    return {"id": f"{scanner}:{rule}:{file}:{line}", "scanner": scanner, "rule": rule, "severity": severity, "file": file, "line": max(1, int(line)), "title": title, "evidence": f"Rule {rule} matched at this location. Source values withheld.", "remediation": remediation, "state": "open"}

def scan(root: Path, rules: Path) -> tuple[list[dict], list[dict]]:
    findings, coverage = [], []
    def execute(name, applicable, function):
        if not applicable:
            coverage.append({"scanner": name, "status": "not_applicable", "count": 0})
            return
        if not shutil.which(name):
            coverage.append({"scanner": name, "status": "unavailable", "count": 0})
            return
        try:
            items = function()
            findings.extend(items)
            coverage.append({"scanner": name, "status": "completed", "count": len(items)})
        except (RuntimeError, ValueError, OSError, KeyError, TypeError) as error:
            coverage.append({"scanner": name, "status": "failed", "count": 0, "reason": str(error) if isinstance(error, RuntimeError) else type(error).__name__})
    def bandit():
        data = run_json(["bandit", "-r", str(root), "-f", "json", "-q"], root)
        if data.get("errors"):
            raise RuntimeError("Incomplete Bandit scan")
        return [finding("bandit", item["test_id"], item["issue_severity"].lower(), safe_path(item["filename"], root), item["line_number"], {"B307": "Dynamic code evaluation", "B602": "Shell command injection risk", "B105": "Embedded credential candidate", "B101": "Assertions used in application code", "B404": "Subprocess module requires review"}.get(item["test_id"], item["test_name"].replace("_", " ").capitalize()), "Review the flagged security pattern and replace it with a safer API. Add a regression test before accepting a change.") for item in data.get("results", [])]
    def semgrep():
        data = run_json(["semgrep", "scan", "--jobs", "1", "--config", str(rules), "--json", "--metrics=off", "--disable-version-check", "--no-git-ignore", str(root)], root)
        if data.get("errors"):
            raise RuntimeError("Incomplete Semgrep scan")
        return [finding("semgrep", item["check_id"].split(".")[-1], SEVERITY.get(item["extra"]["severity"], "medium"), safe_path(item["path"], root), item["start"]["line"], "Unsafe code or credential pattern", "Remove embedded credentials, rotate any real credential, and use managed configuration. Review the rule for other patterns.") for item in data.get("results", [])]
    def pip_audit():
        requirements = []
        for path in root.rglob("requirements*.txt"):
            for line in path.read_text(errors="replace").splitlines():
                if re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+", line.strip()):
                    requirements.append((line.strip(), str(path.relative_to(root))))
        if not requirements:
            raise RuntimeError("No fully pinned requirements")
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "requirements.txt").write_text("\n".join(item[0] for item in requirements))
            data = run_json(["pip-audit", "-r", "requirements.txt", "--no-deps", "--disable-pip", "--progress-spinner", "off", "-f", "json"], work)
        items = []
        for dependency in data.get("dependencies", []):
            for vuln in dependency.get("vulns", []):
                # Database prose is intentionally excluded: only validated IDs and versions.
                identifier = re.sub(r"[^A-Za-z0-9-]", "", vuln["id"])[:80]
                file = next(file for req, file in requirements if req.split("==")[0].lower() == dependency["name"].lower())
                items.append(finding("pip-audit", identifier, "high", file, 1, "Known Python dependency vulnerability", "Review advisory " + identifier + " and update the pinned dependency to a compatible fixed version."))
        return items
    def npm_audit():
        items = []
        for lock in root.rglob("package-lock.json"):
            with tempfile.TemporaryDirectory() as directory:
                work = Path(directory)
                data = json.loads(lock.read_text())
                # Audit lock metadata only. No npm install, lifecycle hooks or repository npmrc.
                (work / "package-lock.json").write_text(json.dumps(data))
                (work / "package.json").write_text('{"name":"sentinel-audit","version":"1.0.0"}')
                result = run_json(["npm", "audit", "--json", "--ignore-scripts", "--registry=https://registry.npmjs.org"], work)
            if result.get("error"):
                raise RuntimeError("Audit service failed")
            for name, value in result.get("vulnerabilities", {}).items():
                items.append(finding("npm", "dependency-advisory", {"moderate": "medium"}.get(value.get("severity"), value.get("severity", "medium")), str(lock.relative_to(root)), 1, "Known JavaScript dependency vulnerability", "Inspect npm audit locally and upgrade the affected dependency. Review breaking changes and test the update."))
        return items
    execute("bandit", any(root.rglob("*.py")), bandit)
    execute("semgrep", True, semgrep)
    execute("pip-audit", any(root.rglob("requirements*.txt")), pip_audit)
    execute("npm", any(root.rglob("package-lock.json")), npm_audit)
    return sorted(findings, key=lambda item: ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(item["severity"], 4), item["file"])), coverage

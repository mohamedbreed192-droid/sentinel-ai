"""Fail on audit errors/new advisories; retain exact, expiring upstream CLI exceptions."""
import json
import sys
from datetime import date
from pathlib import Path
allowed={
("mcp","1.29.0",identifier) for identifier in ["CVE-2026-59951","CVE-2026-116685","CVE-2026-116684","CVE-2026-116686"]
} | {("opentelemetry-api","1.37.0",identifier) for identifier in ["CVE-2026-114603","CVE-2026-126360"]}
data=json.loads(Path(sys.argv[1]).read_text())
if not isinstance(data.get("dependencies"),list) or data.get("errors"):
    sys.exit("Dependency audit did not complete successfully.")
found={(item["name"],item["version"],v["id"]) for item in data["dependencies"] for v in item.get("vulns",[])}
if any(item.get("skip_reason") for item in data["dependencies"]):
    sys.exit("Dependency audit skipped a package; review required.")
if found-allowed:
    sys.exit("New dependency advisories require review: "+str(sorted(found-allowed)))
if found and date.today()>date(2026,12,16):
    sys.exit("Upstream dependency exceptions expired; update Semgrep.")
print(f"Audit completed: {len(found)} known unresolved advisories in documented upstream CLI baseline; no new advisories.")

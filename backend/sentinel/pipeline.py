from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from .graph import architecture, impact_paths
from .importer import import_public
from .scanners import scan
from .patches import propose

RULES = Path(__file__).with_name("rules.yml")

def analyze_directory(root: Path, metadata: dict, demo=False) -> dict:
    root = root.resolve()
    findings, coverage = scan(root, RULES)
    graph = architecture(root, findings)
    for item in findings:
        item["affected"] = impact_paths(graph, item["file"])
        item["proposed_patch"] = propose(root, item)
    weights = {"critical": 25, "high": 12, "medium": 5, "low": 1, "info": 0}
    complete = all(item["status"] in {"completed", "not_applicable"} for item in coverage)
    return {"repository": metadata, "demo": demo, "completed_at": datetime.now(timezone.utc).isoformat(), "findings": findings, "coverage": coverage, "graph": graph, "risk_score": min(100, sum(weights.get(item["severity"], 0) for item in findings)), "coverage_complete": complete, "test_execution": "disabled", "recommendations": "Deterministic guidance. All proposed changes require review and independent tests. No fixes applied."}

def analyze_public(url: str) -> dict:
    with TemporaryDirectory(prefix="sentinel-") as directory:
        root = Path(directory)
        metadata = import_public(url, root)
        return analyze_directory(root, metadata)

def markdown(report: dict) -> str:
    # Strip Markdown control characters from untrusted filenames to prevent injected links/HTML.
    import re
    clean = lambda value: re.sub(r"[^A-Za-z0-9 _./:@+-]", "_", str(value))
    lines = ["# SENTINEL AI reliability report", "", "Repository: " + clean(report["repository"]["name"]), "Commit: " + clean(report["repository"].get("commit", "fixture")), "", f"Risk index: {report['risk_score']}/100 (weighted scanner signals; not a probability)", "Coverage complete: " + str(report["coverage_complete"]), "Repository tests: disabled. No fixes applied.", ""]
    for scanner in report["coverage"]:
        lines.append(f"- {clean(scanner['scanner'])}: {clean(scanner['status'])}")
    for item in report["findings"]:
        lines += ["", "## " + clean(item["title"]), f"{clean(item['severity'])} | {clean(item['file'])}:{item['line']}", clean(item["evidence"]), clean(item["remediation"])]
    return "\n".join(lines)

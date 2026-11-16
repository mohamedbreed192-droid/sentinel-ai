import ast
from collections import Counter
from pathlib import Path
import re

SUFFIXES = {".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript"}

def architecture(root: Path, findings: list[dict]) -> dict:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    sources = [path for path in files if path.suffix in SUFFIXES]
    languages = Counter(SUFFIXES[path.suffix] for path in sources)
    names = {str(path.relative_to(root)): path for path in sources}
    module_map = {str(path.relative_to(root).with_suffix("")).replace("/", ".").removesuffix(".__init__"): str(path.relative_to(root)) for path in sources if path.suffix == ".py"}
    edges = set()
    for relative, path in names.items():
        content = path.read_text(errors="replace")
        if path.suffix == ".py":
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    parent = relative[:-3].replace("/", ".").split(".")[:-node.level] if node.level else []
                    base = ".".join(parent + ([node.module] if node.module else []))
                    imported.extend([base, *[f"{base}.{alias.name}".strip(".") for alias in node.names]])
            for module in imported:
                target = module_map.get(module)
                if target and target != relative:
                    edges.add((relative, target))
        else:
            for match in re.findall(r"(?:from\s*|import\s*)[\"'](\.[^\"']+)[\"']", content):
                base = (path.parent / match).resolve()
                for candidate in [base, *[Path(str(base) + suffix) for suffix in (".ts", ".tsx", ".js", ".jsx")], base / "index.ts"]:
                    try:
                        target = str(candidate.relative_to(root.resolve()))
                    except ValueError:
                        continue
                    if target in names:
                        edges.add((relative, target))
    nodes = [{"id": relative, "label": Path(relative).name, "findings": [f["id"] for f in findings if f["file"] == relative]} for relative in names]
    frameworks = [name for name, pattern in [("pytest", "test_*.py"), ("Playwright", "playwright.config.*"), ("Jest", "jest.config.*")] if any(root.rglob(pattern))]
    manifests = [str(path.relative_to(root)) for path in files if path.name in {"package.json", "package-lock.json", "pyproject.toml", "requirements.txt"}]
    return {"nodes": nodes, "edges": [{"source": source, "target": target} for source, target in sorted(edges)], "languages": dict(languages), "files": len(files), "source_files": len(sources), "test_frameworks": frameworks, "manifests": manifests, "summary": f"{len(sources)} source modules across {len(languages)} languages; {len(edges)} resolved local import relationships. Dynamic imports and runtime service calls are not modeled."}

def impact_paths(graph: dict, file: str) -> list[str]:
    # Reverse reachability answers which local importers may depend on this file.
    affected, queue = {file}, [file]
    while queue:
        target = queue.pop()
        for edge in graph["edges"]:
            if edge["target"] == target and edge["source"] not in affected:
                affected.add(edge["source"])
                queue.append(edge["source"])
    return sorted(affected)

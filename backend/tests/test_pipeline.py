import json
from pathlib import Path
from sentinel.graph import architecture, impact_paths
from sentinel.pipeline import analyze_directory, markdown
from sentinel.patches import propose

FIXTURE = Path(__file__).resolve().parents[2]/"fixtures"/"demo"

def test_real_scanners_and_secret_redaction():
    report=analyze_directory(FIXTURE,{"name":"sentinel/demo"},demo=True)
    statuses={item["scanner"]:item["status"] for item in report["coverage"]}
    assert statuses["bandit"]=="completed"
    assert statuses["semgrep"]=="completed", next(item for item in report["coverage"] if item["scanner"]=="semgrep")
    assert any(item["rule"]=="B307" for item in report["findings"])
    assert any(item["rule"]=="embedded-credential" for item in report["findings"])
    assert "SENTINEL_SYNTHETIC_CREDENTIAL_DO_NOT_USE" not in json.dumps(report)
    assert "SENTINEL_SYNTHETIC_CREDENTIAL_DO_NOT_USE" not in markdown(report)
    assert report["test_execution"]=="disabled"
    assert any(item.get("proposed_patch") for item in report["findings"])

def test_import_graph_and_cycles(tmp_path):
    (tmp_path/"a.py").write_text("from b import value\n")
    (tmp_path/"b.py").write_text("import a\nvalue = 1\n")
    graph=architecture(tmp_path,[])
    assert {tuple(edge.values()) for edge in graph["edges"]}=={("a.py","b.py"),("b.py","a.py")}
    assert impact_paths(graph,"b.py")==["a.py","b.py"]

def test_relative_imports(tmp_path):
    (tmp_path/"pkg").mkdir()
    (tmp_path/"pkg/a.py").write_text("from .b import value\n")
    (tmp_path/"pkg/b.py").write_text("value = 1\n")
    assert {"source":"pkg/a.py","target":"pkg/b.py"} in architecture(tmp_path,[])["edges"]

def test_patch_exports_no_surrounding_secret(tmp_path):
    (tmp_path/"a.py").write_text('"""Docstring"""\nfrom __future__ import annotations\nSECRET = "DO_NOT_EXPORT"\ndef parse(value):\n    return eval(value)\n')
    result=propose(tmp_path,{"file":"a.py","line":5,"rule":"B307"})
    assert result and "DO_NOT_EXPORT" not in result["diff"]
    assert "+import ast" in result["diff"]
    assert "ast.literal_eval(value)" in result["diff"]
    assert not result["verified"]

def test_no_patch_for_complex_eval(tmp_path):
    (tmp_path/"a.py").write_text('x = eval("potential source secret")\n')
    assert propose(tmp_path,{"file":"a.py","line":1,"rule":"B307"}) is None

def test_scanner_failure_is_not_clean(tmp_path,monkeypatch):
    from sentinel import scanners
    monkeypatch.setattr(scanners.shutil,"which",lambda _:None)
    report=analyze_directory(tmp_path,{"name":"empty"})
    assert report["findings"]==[]
    assert not report["coverage_complete"]
    assert report["coverage"][1]["status"]=="unavailable"

def test_dependency_adapters_keep_installers_disabled(tmp_path,monkeypatch):
    from sentinel import scanners
    (tmp_path/"requirements.txt").write_text('urllib3==1.26.5\n-r external.txt\nhttps://example.com/package.whl\n')
    (tmp_path/"package-lock.json").write_text('{"lockfileVersion":3,"packages":{}}')
    commands=[]
    def fake(command,cwd,accepted=(0,1)):
        commands.append(command)
        if command[0]=="pip-audit":
            assert (cwd/"requirements.txt").read_text()=="urllib3==1.26.5"
            return {"dependencies":[{"name":"urllib3","vulns":[{"id":"CVE-TEST-001","fix_versions":["2.0"]}]}]}
        if command[0]=="npm":
            assert "--ignore-scripts" in command
            assert not (cwd/".npmrc").exists()
            return {"vulnerabilities":{"sample":{"severity":"moderate"}}}
        return {"results":[]}
    monkeypatch.setattr(scanners,"run_json",fake)
    monkeypatch.setattr(scanners.shutil,"which",lambda name:name)
    findings,coverage=scanners.scan(tmp_path,Path("rules.yml"))
    assert next(item for item in findings if item["scanner"]=="npm")["severity"]=="medium"
    assert all(item["status"] in {"completed","not_applicable"} for item in coverage)
    pip=next(command for command in commands if command[0]=="pip-audit")
    assert "--no-deps" in pip and "--disable-pip" in pip


def test_skipped_dependency_is_partial_coverage(tmp_path,monkeypatch):
    from sentinel import scanners
    (tmp_path/"requirements.txt").write_text("unknown-package==0.0.0\n")
    monkeypatch.setattr(scanners.shutil,"which",lambda name:name)
    def fake(command,cwd,accepted=(0,1)):
        if command[0]=="pip-audit":
            return {"dependencies":[{"name":"unknown-package","skip_reason":"Not found"}]}
        return {"results":[]}
    monkeypatch.setattr(scanners,"run_json",fake)
    findings,coverage=scanners.scan(tmp_path,Path("rules.yml"))
    status=next(item for item in coverage if item["scanner"]=="pip-audit")
    assert status["status"]=="failed" and status["count"]==0


def test_real_typescript_credential_rule(tmp_path):
    (tmp_path/"config.ts").write_text('const API_TOKEN = "SYNTHETIC_JS_VALUE";\n')
    report=analyze_directory(tmp_path,{"name":"fixture/js"})
    assert next(item for item in report["coverage"] if item["scanner"]=="semgrep")["status"]=="completed"
    assert any(item["rule"]=="embedded-credential-js" for item in report["findings"])
    assert "SYNTHETIC_JS_VALUE" not in json.dumps(report)

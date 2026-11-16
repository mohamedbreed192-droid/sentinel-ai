"""Narrow, unverified patch proposals; no surrounding source is exported."""
import ast
import difflib
from pathlib import Path
import re

def propose(root: Path, item: dict) -> dict | None:
    if item["rule"] not in {"B307", "python-eval"}:
        return None
    path = root / item["file"]
    try:
        before = path.read_text().splitlines(keepends=True)
        line_index = item["line"] - 1
        line = before[line_index]
        if not re.fullmatch(r"\s*(?:return|[A-Za-z_]\w*\s*=)\s*eval\([A-Za-z_]\w*\)\s*", line):
            return None
        tree = ast.parse("".join(before))
        # Refuse shadowed 'ast' names; proposal remains unverified for semantics/resource use.
        if any(isinstance(node, ast.Name) and node.id == "ast" for node in ast.walk(tree)):
            return None
        insert = 0
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                insert = node.end_lineno
            elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
                insert = node.end_lineno
            else:
                break
        after = list(before)
        after[line_index] = line.replace("eval(", "ast.literal_eval(")
        after.insert(insert, "import ast\n")
        diff = "".join(difflib.unified_diff(before, after, fromfile="a/"+item["file"], tofile="b/"+item["file"], n=0))
        function = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.lineno <= item["line"] <= node.end_lineno), None)
        module = item["file"].removesuffix(".py").replace("/", ".")
        test_code = None
        if function and all(part.isidentifier() for part in module.split(".")) and len(function.args.args) == 1:
            test_code = f"import pytest\nfrom {module} import {function.name}\n\ndef test_bounded_literal_input():\n    assert {function.name}('[1, 2]') == [1, 2]\n\ndef test_function_call_is_rejected():\n    with pytest.raises((ValueError, SyntaxError)):\n        {function.name}(\"__import__('os').getcwd()\")\n"
        return {"test_code": test_code, "diff": diff, "verified": False, "tradeoffs": "Only appropriate for Python literal parsing. Reject oversized input and catch parse errors. This changes expression semantics; review requirements and run regression tests.", "tests": ["Accept bounded supported literals", "Reject function calls and attribute access", "Reject oversized and malformed input"]}
    except (OSError, IndexError, SyntaxError):
        return None

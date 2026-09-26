from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .repository import read_repo_file


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _finding(severity: str, category: str, path: str, line: int, title: str, evidence: str, fix: str, kind: str) -> dict[str, Any]:
    return {"id": f"{path}:{line}:{title[:16]}", "severity": severity, "category": category, "file": path,
            "line": line, "line_start": line, "line_end": line, "symbol": "", "title": title, "problem": title,
            "evidence": evidence.strip()[:260], "impact": "Potential risk; validate in context.",
            "recommendation": fix, "suggested_fix": fix, "confidence": "Potential issue — verify in context",
            "confidence_score": 0.65, "kind": kind}


def scan_repository(repo: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    try:
        import json
        file_rows = repo.get("files", [])
        for file_row in file_rows:
            path = file_row["path"]
            suffix = Path(path).suffix.lower()
            if suffix not in {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".env"}:
                continue
            content = read_repo_file(repo, path)
            lines = content.splitlines()
            symbols = file_row.get("symbols", [])
            def enrich(finding: dict[str, Any]) -> dict[str, Any]:
                symbol = next((item for item in symbols if item["line_start"] <= finding["line"] <= item["line_end"]), None)
                if symbol:
                    finding["symbol"] = symbol["name"]
                return finding
            for index, line in enumerate(lines, 1):
                stripped = line.strip()
                if re.search(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", line) and not re.search(r"(?i)(your_|example|placeholder|changeme|replace_me|<.*>)", line):
                    findings.append(enrich(_finding("HIGH", "Security", path, index, "Potential hard-coded credential", line, "Move the value to an environment variable and rotate it if it was exposed.", "security")))
                if re.search(r"\beval\s*\(", line):
                    findings.append(enrich(_finding("HIGH", "Security", path, index, "Dynamic code execution via eval", line, "Avoid evaluating untrusted strings; use an explicit parser or allow-listed dispatch.", "security")))
                if re.search(r"subprocess\.(?:run|Popen|call).*shell\s*=\s*True", line):
                    findings.append(enrich(_finding("HIGH", "Security", path, index, "Shell execution enabled", line, "Pass an argument list with shell=False and validate untrusted input.", "security")))
                if re.search(r"execute\s*\(\s*f['\"]|execute\s*\([^\n]*%\s*\(", line, re.I):
                    findings.append(enrich(_finding("HIGH", "Security", path, index, "Possible SQL string interpolation", line, "Use parameterized SQL placeholders and bind values separately.", "security")))
                if re.search(r"cors.*allow_origins.*\*|allow_origins\s*=\s*\[['\"]\*['\"]\]", line, re.I):
                    findings.append(enrich(_finding("MEDIUM", "Security", path, index, "Wildcard CORS origin", line, "Restrict browser origins to the deployment domains that need access.", "security")))
                if re.search(r"\bexcept\s*:\s*(?:#.*)?$", line):
                    findings.append(enrich(_finding("LOW", "Error Handling", path, index, "Bare exception handler", line, "Catch expected exception types and preserve useful error details.", "bug")))
                if re.search(r"\b(?:TODO|FIXME)\b", line):
                    findings.append(enrich(_finding("INFO", "Maintainability", path, index, "Unresolved TODO marker", line, "Confirm whether this task is still relevant and track it if needed.", "bug")))
            if suffix == ".py":
                try:
                    ast.parse(content)
                except SyntaxError as exc:
                    lineno = exc.lineno or 1
                    evidence = lines[lineno - 1] if 0 < lineno <= len(lines) else exc.msg
                    findings.append(_finding("HIGH", "Runtime", path, lineno, "Python syntax error", evidence, "Fix the reported syntax error before running this module.", "bug"))
            if path.endswith("package.json"):
                try:
                    json.loads(content)
                except json.JSONDecodeError as exc:
                    findings.append(_finding("MEDIUM", "Runtime", path, exc.lineno, "Invalid package.json", lines[exc.lineno - 1] if exc.lineno <= len(lines) else exc.msg, "Repair the JSON syntax so package managers can read dependencies.", "bug"))
    except (OSError, ValueError):
        return findings
    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["file"], item["line"]))
    return findings[:200]


def code_quality(repo: dict[str, Any]) -> dict[str, Any]:
    files = repo.get("files", [])
    tests = repo.get("test_files", [])
    readme = bool(repo.get("has_docs"))
    # These are coverage indicators, not a claim of test or security correctness.
    return {"test_files": len(tests), "documentation_present": readme,
            "large_files": sum(1 for f in files if f.get("lines", 0) > 600),
            "empty_files": sum(1 for f in files if f.get("lines", 0) == 0)}


def make_plan(requirement: str, repo: dict[str, Any]) -> list[dict[str, str]]:
    candidates = repo.get("entry_points", [])[:2] or repo.get("tree", [])[:3]
    return [
        {"step": "Clarify behavior", "detail": f"Turn ‘{requirement[:120]}’ into acceptance criteria and note security or compatibility constraints."},
        {"step": "Locate integration points", "detail": "Start with " + (", ".join(f"`{p}`" for p in candidates) if candidates else "the repository structure; select the relevant module after inspection.")},
        {"step": "Implement the smallest change", "detail": "Add the feature behind existing architecture conventions and keep secrets/configuration outside source."},
        {"step": "Verify and document", "detail": f"Add focused tests in {', '.join(repo.get('test_files', [])[:2]) or 'a new tests/ module'}, run the relevant checks, and update developer documentation."},
    ]


def make_tests(repo: dict[str, Any], target: str = "", request: str = "") -> dict[str, str]:
    files = repo.get("files", [])
    selected = next((f for f in files if target and target in f["path"]), None)
    if selected is None:
        selected = next((
            f for f in files
            if f.get("language") == "Python"
            and Path(f["path"]).name != "__init__.py"
            and not any(part.lower() in {"test", "tests"} for part in Path(f["path"]).parts)
        ), None)
    path = selected["path"] if selected else (repo.get("entry_points") or repo.get("tree") or [""])[0]
    name = Path(path).stem or "module"
    excerpt = ""
    if path:
        try:
            excerpt = read_repo_file(repo, path)
        except (OSError, ValueError):
            pass
    # Runtime generation is honest and language-aware; Python is the first target.
    if selected and selected.get("language") == "Python":
        functions = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)", excerpt, re.M)
        funcs = [fn for fn, _ in functions if not fn.startswith("_")][:4]
        module = ".".join((*Path(path).with_suffix("").parts[:-1], name))
        if funcs:
            code = f"from {module} import {', '.join(funcs)}\n\n"
            code += "\n".join(
                f"def test_{fn}_is_public():\n    # TODO: Add realistic inputs and assert the documented behavior.\n    assert callable({fn})\n"
                for fn in funcs
            )
        else:
            code = f"import {module}\n\n\ndef test_module_imports():\n    # TODO: Add behavior-focused tests after identifying public module functions.\n    assert {module} is not None\n"
        return {"language": "Python", "file": f"tests/test_{name}.py", "code": code, "note": f"Draft generated from `{path}`. Replace the callable checks with behavior assertions before relying on it."}
    code = f"// Draft tests for {path or 'selected module'}\n// Request: {request or 'Cover normal, boundary, and invalid input.'}\ndescribe('{name}', () => {{\n  it('handles a valid input', () => {{\n    // Import the target and assert its documented result.\n    expect(true).toBe(true);\n  }});\n}});"
    return {"language": "TypeScript / JavaScript", "file": f"tests/{name}.test.ts", "code": code, "note": "Template only; adapt imports and assertions to the target framework."}

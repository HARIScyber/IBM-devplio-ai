from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .analysis import make_plan
from .config import DEMO_DIR
from .repository import read_repo_file
from .retrieval import retrieve


DEMO_ISSUES = {
    1: {
        "number": 1,
        "title": "Email lookup fails when input contains whitespace",
        "body": "A user whose saved email is alice@example.com cannot be found when the submitted address is ' Alice@Example.com '. Case should be ignored, and surrounding whitespace should be trimmed.",
        "labels": ["bug", "authentication"],
        "stack_trace": "",
    }
}

DEMO_AUTH_BEFORE = '''def find_account(accounts: list[dict], email: str) -> dict | None:
    """Return the matching account, if present."""
    for account in accounts:
        if account.get("email", "").lower() == email.lower():
            return account
    return None
'''
DEMO_AUTH_AFTER = '''def find_account(accounts: list[dict], email: str) -> dict | None:
    """Return the matching account, if present."""
    normalized_email = email.strip().lower()
    for account in accounts:
        if account.get("email", "").strip().lower() == normalized_email:
            return account
    return None
'''
DEMO_REGRESSION_TEST = '''from backend.auth import find_account


def test_find_account_trims_whitespace_and_ignores_email_case():
    account = {"email": "alice@example.com", "id": "acct-1"}
    assert find_account([account], " Alice@Example.com ") is account
'''


def investigate(repo: dict[str, Any], issue: dict[str, Any]) -> dict[str, Any]:
    query = " ".join((issue.get("title", ""), issue.get("body", ""), issue.get("stack_trace", "")))
    evidence = retrieve(repo, query, limit=8)
    is_demo_issue = repo.get("source") == "demo/sample-repository" and issue.get("number") == 1 and issue.get("origin", "demo") == "demo"
    if is_demo_issue:
        path = "backend/auth.py"
        text = read_repo_file(repo, path)
        lines = text.splitlines()
        start, end = 4, 9
        excerpt = "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, min(end, len(lines)) + 1))
        symbol = "find_account"
        return {
            "issue": issue.get("title", ""),
            "root_cause": "find_account lowercases both email values but does not trim surrounding whitespace before comparing them.",
            "confidence": 0.99,
            "affected_files": [path],
            "affected_symbols": [symbol],
            "evidence": [{"file_path": path, "symbol": symbol, "line_start": start, "line_end": min(end, len(lines)), "excerpt": excerpt}],
            "recommendations": ["Normalize the incoming address and stored address with strip().lower() before comparing.", "Add a regression test for mixed case and leading/trailing whitespace."],
        }
    if evidence:
        first = evidence[0]
        return {
            "issue": issue.get("title", ""),
            "root_cause": "The indexed evidence is related to this issue, but does not establish a root cause. Review the cited code before proposing a fix.",
            "confidence": 0.25,
            "affected_files": list(dict.fromkeys(item["file"] for item in evidence[:4])),
            "affected_symbols": [first.get("symbol", "")] if first.get("symbol") else [],
            "evidence": [{"file_path": item["file"], "symbol": item.get("symbol", ""), "line_start": item.get("line_start", item["line"]), "line_end": item.get("line_end", item["line"]), "excerpt": item["excerpt"]} for item in evidence],
            "recommendations": ["Confirm the expected behavior with a reproducing test.", "Inspect the cited source and related tests before selecting a patch."],
        }
    return {
        "issue": issue.get("title", ""),
        "root_cause": "No relevant source evidence was found, so a root cause cannot be determined yet.",
        "confidence": 0.0,
        "affected_files": [],
        "affected_symbols": [],
        "evidence": [],
        "recommendations": ["Check that the correct repository is indexed.", "Add a stack trace, symbol name, or concrete reproduction steps."],
    }


def plan_workflow(requirement: str, repo: dict[str, Any], investigation: dict[str, Any]) -> list[dict[str, Any]]:
    base = make_plan(requirement, repo)
    affected = investigation.get("affected_files", [])
    return [
        {"step": item["step"], "detail": item["detail"], "files_to_modify": affected if index == 2 else []}
        for index, item in enumerate(base)
    ]


def propose_patch(repo: dict[str, Any], investigation: dict[str, Any]) -> dict[str, Any]:
    if repo.get("source") != "demo/sample-repository" or "find_account" not in investigation.get("affected_symbols", []):
        raise ValueError("Patch generation is enabled only for the bundled issue with a known, evidence-backed fix.")
    path = "backend/auth.py"
    before = read_repo_file(repo, path)
    if DEMO_AUTH_BEFORE not in before:
        raise ValueError("The demo source differs from the reviewed baseline; refusing to propose a stale patch.")
    after = before.replace(DEMO_AUTH_BEFORE, DEMO_AUTH_AFTER, 1)
    diff = "\n".join(difflib.unified_diff(
        before.splitlines(), after.splitlines(), fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""
    ))
    additions = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    deletions = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    return {
        "files": [{"file_path": path, "symbol": "find_account", "before": before, "after": after}],
        "unified_diff": diff,
        "additions": additions,
        "deletions": deletions,
        "changed_symbols": ["find_account"],
        "risk_warnings": ["Patch is a deterministic demo proposal. Review behavior and surrounding code before approval."],
        "applied_to_repository": False,
    }


def regression_test() -> dict[str, str]:
    return {
        "file": "tests/test_workflow_regression.py",
        "code": DEMO_REGRESSION_TEST,
        "expected_behavior": "An email lookup succeeds when casing differs and the submitted address contains surrounding whitespace.",
        "framework": "pytest",
    }


def _run_pytest(workspace: Path) -> dict[str, Any]:
    env_keys = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA")
    env = {key: os.environ[key] for key in env_keys if os.environ.get(key)}
    env.update({"PYTHONPATH": str(workspace), "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    command = [sys.executable, "-m", "pytest", "-q", "tests/test_workflow_regression.py"]
    try:
        result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True,
                                timeout=12, check=False, shell=False)
        status = "PASS" if result.returncode == 0 else "FAIL"
        return {"status": status, "command": "python -m pytest -q tests/test_workflow_regression.py",
                "exit_code": result.returncode, "stdout": result.stdout[-6000:], "stderr": result.stderr[-3000:]}
    except subprocess.TimeoutExpired as exc:
        return {"status": "TIMEOUT", "command": "python -m pytest -q tests/test_workflow_regression.py",
                "exit_code": None, "stdout": str(exc.stdout or "")[-6000:], "stderr": str(exc.stderr or "")[-3000:]}
    except OSError as exc:
        return {"status": "ERROR", "command": "python -m pytest -q tests/test_workflow_regression.py",
                "exit_code": None, "stdout": "", "stderr": f"Could not start the allowed verifier: {type(exc).__name__}"}


def verify_demo(repo: dict[str, Any], patch: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
    if repo.get("source") != "demo/sample-repository" or repo.get("id") != "demo-devpilot":
        raise ValueError("Safe verification currently runs only against the bundled demo repository.")
    if test.get("framework") != "pytest" or test.get("file") != "tests/test_workflow_regression.py":
        raise ValueError("The verifier accepts only the generated demo pytest regression test.")
    files = patch.get("files", [])
    if len(files) != 1 or files[0].get("file_path") != "backend/auth.py":
        raise ValueError("The verifier accepts only the allow-listed demo authentication patch.")
    with tempfile.TemporaryDirectory(prefix="devpilot-verify-") as temporary:
        workspace = Path(temporary)
        shutil.copytree(DEMO_DIR, workspace, dirs_exist_ok=True)
        test_path = workspace / "tests" / "test_workflow_regression.py"
        test_path.write_text(test["code"], encoding="utf-8")
        before = _run_pytest(workspace)
        relative = PurePosixPath(files[0]["file_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("The proposed patch contains an unsafe path.")
        target = workspace.joinpath(*relative.parts).resolve()
        if workspace.resolve() not in target.parents:
            raise ValueError("The proposed patch escapes the temporary workspace.")
        current = target.read_text(encoding="utf-8")
        if current != files[0]["before"]:
            raise ValueError("The temporary source no longer matches the patch baseline.")
        target.write_text(files[0]["after"], encoding="utf-8")
        after = _run_pytest(workspace)
        expected = before["status"] == "FAIL" and after["status"] == "PASS"
        status = "PASS" if expected else ("ERROR" if "ERROR" in (before["status"], after["status"]) or "TIMEOUT" in (before["status"], after["status"]) else "FAIL")
        return {
            "status": status,
            "isolation": "Temporary copy of the bundled demo; source repository was not modified.",
            "before": before,
            "after": after,
            "changed_files": [files[0]["file_path"], test["file"]],
            "expected_before_failure": before["status"] == "FAIL",
            "expected_after_pass": after["status"] == "PASS",
        }


def review_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    verification = workflow.get("verification") or {}
    passed = verification.get("status") == "PASS"
    return {
        "status": "READY_FOR_HUMAN_REVIEW" if passed else "NEEDS_ATTENTION",
        "correctness": "Regression test failed before the proposed patch and passed after it." if passed else "The expected before/after verification was not established.",
        "regression_risk": "Low for the demonstrated input; broader account lookup behavior still needs review." if passed else "Unverified.",
        "security": "The patch trims and lowercases email values; no credential or execution behavior changes.",
        "maintainability": "The normalization is explicit and local to the affected function.",
        "test_coverage": "One focused regression case was run in the temporary demo workspace.",
        "review_notes": ["Review the diff and surrounding call sites before applying it to a real repository.", "No automatic repository write, merge, or push occurred."],
    }

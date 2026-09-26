from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .agents import OrchestratorAgent
from .analysis import code_quality, make_plan, make_tests, scan_repository
from .config import MAX_REPOSITORY_MB, STORAGE_DIR
from .repository import analyze_path, copy_demo, download_github, extract_zip
from .schemas import (AnalyzeRequest, ChatRequest, GenerateRequest, PlanRequest, ReviewRequest,
                      WorkflowApprovalRequest, WorkflowPlanRequest, WorkflowRecord, WorkflowInvestigationRequest)
from .workflow import DEMO_ISSUES, investigate, plan_workflow, propose_patch, regression_test, review_workflow, verify_demo
from .evaluation import run_benchmark


@asynccontextmanager
async def lifespan(_: FastAPI):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    database.init_db()
    yield


app = FastAPI(title="DevPilot AI API", version="0.1.0", description="Repository-aware software engineering workflows", lifespan=lifespan)
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
origins.extend(value.strip() for value in os.getenv("CORS_ORIGINS", "").split(",") if value.strip())
frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if frontend_url:
    origins.append(frontend_url)
origins = list(dict.fromkeys(origins))
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
class _JsonRequestFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                           "event": record.getMessage(), "request_id": getattr(record, "request_id", None),
                           "operation": getattr(record, "operation", None), "duration_ms": getattr(record, "duration_ms", None),
                           "status": getattr(record, "status", None)}, separators=(",", ":"))


logger = logging.getLogger("devpilot.api")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(_JsonRequestFormatter())
    logger.addHandler(_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
logger.propagate = False


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = uuid4().hex
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info("api_request", extra={
            "request_id": request_id,
            "operation": f"{request.method} {request.url.path}",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "status": status_code,
        })


def _require_repo(repo_id: str) -> dict[str, Any]:
    repo = database.get_repository(repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found. Try the bundled demo repository.")
    if not Path(repo["root"]).is_dir():
        raise HTTPException(404, "Repository files are no longer available. Re-analyze the repository.")
    return repo


def _public_repo(repo: dict[str, Any]) -> dict[str, Any]:
    """Return repository metadata without local paths or duplicated source indexes."""
    return {key: value for key, value in repo.items() if key not in {"root", "snippet_index", "chunks"}}


def _index(root: Path, name: str, source: str, repo_id: str) -> dict[str, Any]:
    repo = analyze_path(root, name, source, repo_id)
    database.save_repository(repo_id, name, source, str(root), repo)
    repo["findings"] = scan_repository({**repo, "root": str(root)})
    repo["quality"] = code_quality(repo)
    return repo


@app.get("/api/health")
async def health() -> dict[str, Any]:
    demo = os.getenv("DEMO_MODE", "true").lower() == "true"
    return {"status": "ok", "service": "DevPilot AI", "demo_mode": demo, "provider": os.getenv("LLM_PROVIDER", "mock")}


@app.post("/api/repositories/demo")
async def demo_repository() -> dict[str, Any]:
    repo_id, root, source = copy_demo()
    return _public_repo(_index(root, "sample-repository", source, repo_id))


@app.post("/api/repositories/analyze")
async def analyze_repository(body: AnalyzeRequest) -> dict[str, Any]:
    try:
        # Without per-user GitHub authorization, do not use a server credential
        # to let an anonymous caller import private repositories.
        name, archive = await download_github(str(body.url))
        repo_id = hashlib.sha256(archive).hexdigest()[:12]
        _, root = extract_zip(archive, name)
        return _public_repo(_index(root, name, str(body.url), repo_id))
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)[:300]
        raise HTTPException(400, f"Repository analysis failed: {detail}") from exc


@app.post("/api/repositories/upload")
async def upload_repository(file: UploadFile = File(...)) -> dict[str, Any]:
    # Uploaded source is user-owned data. Until authentication and ownership
    # isolation exist, accepting it would expose it through anonymous repo APIs.
    raise HTTPException(503, "ZIP uploads are temporarily unavailable until secure user accounts and repository ownership are configured.")


@app.get("/api/repositories/{repo_id}")
async def get_repository(repo_id: str) -> dict[str, Any]:
    repo = _require_repo(repo_id)
    repo["findings"] = scan_repository(repo)
    repo["quality"] = code_quality(repo)
    return _public_repo(repo)


@app.post("/api/chat")
async def chat(body: ChatRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    result = await OrchestratorAgent(repo).answer(body.question)
    database.save_chat(body.repository_id, body.question, result["answer"])
    database.add_activity(body.repository_id, "Repository question", body.question[:180])
    return result


@app.post("/api/analyze/bugs")
async def analyze_bugs(body: GenerateRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    findings = [item for item in scan_repository(repo) if item["kind"] == "bug"]
    return {"findings": findings, "summary": f"Found {len(findings)} potential code-quality or runtime findings using static checks.", "source": "static analysis"}


@app.post("/api/analyze/security")
async def analyze_security(body: GenerateRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    findings = [item for item in scan_repository(repo) if item["kind"] == "security"]
    return {"findings": findings, "summary": f"Found {len(findings)} potential security findings using local pattern checks.", "source": "static analysis"}


@app.post("/api/generate/tests")
async def generate_tests(body: GenerateRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    result = make_tests(repo, body.target, body.request)
    database.add_activity(body.repository_id, "Test draft generated", result["file"])
    return result


@app.post("/api/generate/docs")
async def generate_docs(body: GenerateRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    components = ", ".join(repo.get("components", [])) or "repository root"
    endpoints = ", ".join(f"`{path}`" for path in repo.get("api_endpoints", [])) or "No route decorators found in indexed files."
    readme = f"# {repo['name']}\n\n> Draft generated from repository metadata; review before publishing.\n\n## Overview\n\nPrimary language: {repo.get('primary_language', 'Unknown')}. Detected frameworks: {', '.join(repo.get('frameworks', [])) or 'none identified'}.\n\n## Structure\n\nTop-level components: {components}.\n\n## Entry points\n\n" + "\n".join(f"- `{path}`" for path in repo.get("entry_points", [])) + f"\n\n## API routes detected\n\n{endpoints}\n\n## Development\n\nInspect the configuration files listed in the DevPilot repository overview, install the project dependencies, and run the existing test suite."
    return {"title": "Repository overview draft", "content": readme, "note": "Preview only. Review all generated statements and paths before applying."}


@app.post("/api/generate/plan")
async def generate_plan(body: PlanRequest) -> dict[str, Any]:
    repo = _require_repo(body.repository_id)
    plan = make_plan(body.requirement, repo)
    database.add_activity(body.repository_id, "Development plan generated", body.requirement[:180])
    return {"requirement": body.requirement, "steps": plan, "mode": "repository-aware MVP planner"}


@app.post("/api/review")
async def review_diff(body: ReviewRequest) -> dict[str, Any]:
    lines = body.diff.splitlines()
    additions = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    deletions = [line[1:] for line in lines if line.startswith("-") and not line.startswith("---")]
    risks = []
    for index, line in enumerate(additions, 1):
        if any(marker in line.lower() for marker in ("password =", "api_key =", "secret =")):
            risks.append({"severity": "HIGH", "title": "Possible hard-coded secret", "evidence": line[:250], "line_in_added_hunks": index})
        if "eval(" in line:
            risks.append({"severity": "HIGH", "title": "Dynamic eval call added", "evidence": line[:250], "line_in_added_hunks": index})
    return {"summary": f"Diff contains {len(additions)} added and {len(deletions)} removed lines.", "potential_bugs": [], "security_concerns": risks,
            "breaking_changes": [], "testing_suggestions": ["Run focused unit tests for changed behavior", "Exercise boundary and error cases"],
            "documentation_changes": ["Update user or API documentation if behavior changed"], "source": "basic diff heuristics; human review required"}


async def _github_list(kind: str) -> dict[str, Any]:
    # This endpoint is anonymous, so only public GitHub data may be fetched.
    # Never use a server-wide token until per-user authorization exists.
    repo_slug = os.getenv("GITHUB_REPOSITORY", "")
    if not repo_slug or "/" not in repo_slug:
        return {"items": [], "configured": False, "message": "Set GITHUB_REPOSITORY=owner/repository to read public GitHub issues. Private repositories require per-user authorization."}
    endpoint = "issues?state=open" if kind == "issues" else "pulls?state=open"
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"https://api.github.com/repos/{repo_slug}/{endpoint}", headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
        rows = response.json()
        return {"items": [{"number": row["number"], "title": row["title"], "body": (row.get("body") or "")[:8000], "labels": [label.get("name", "") for label in row.get("labels", [])], "repository": repo_slug, "state": row["state"], "url": row["html_url"], "user": row.get("user", {}).get("login", "unknown")} for row in rows[:30] if not (kind == "issues" and "pull_request" in row)], "configured": True}
    except Exception as exc:
        return {"items": [], "configured": True, "message": f"GitHub request failed: {str(exc)[:160]}"}


@app.get("/api/issues")
async def issues() -> dict[str, Any]:
    return await _github_list("issues")


@app.get("/api/pull-requests")
async def pull_requests() -> dict[str, Any]:
    return await _github_list("pulls")


@app.get("/api/activity")
async def activity() -> dict[str, Any]:
    return {"items": database.recent_activity()}


@app.get("/api/evaluation/run")
async def evaluation_run() -> dict[str, Any]:
    return run_benchmark()


def _get_workflow(workflow_id: str) -> dict[str, Any]:
    workflow = database.get_workflow(workflow_id)
    if (not workflow or workflow.get("repository_id") != "demo-devpilot"
            or workflow.get("issue", {}).get("origin") != "demo"
            or workflow.get("issue", {}).get("number") != 1):
        raise HTTPException(404, "Workflow not found.")
    return workflow


def _save_workflow(workflow: dict[str, Any]) -> WorkflowRecord:
    workflow["updated_at"] = datetime.now(timezone.utc).isoformat()
    database.save_workflow(workflow)
    return WorkflowRecord.model_validate(workflow)


@app.get("/api/workflow/demo-issues")
async def workflow_demo_issues() -> dict[str, Any]:
    return {"items": list(DEMO_ISSUES.values()), "source": "bundled demo issues"}


@app.get("/api/workflow", response_model=list[WorkflowRecord])
async def list_workflows(repository_id: str | None = None) -> list[WorkflowRecord]:
    if repository_id not in (None, "demo-devpilot"):
        return []
    rows = database.recent_workflows(repository_id="demo-devpilot")
    return [WorkflowRecord.model_validate(item) for item in rows
            if item.get("issue", {}).get("origin") == "demo" and item.get("issue", {}).get("number") == 1]


@app.post("/api/workflow/investigate", response_model=WorkflowRecord)
async def workflow_investigate(body: WorkflowInvestigationRequest) -> WorkflowRecord:
    if not body.issue_number and (not body.issue_title or not body.issue_body):
        raise HTTPException(422, "Issue title and description are required for investigation.")
    # Anonymous workflows are stored in the shared demo database. Accept only
    # the fixed bundled issue so caller-supplied issue text cannot leak to others.
    if body.repository_id != "demo-devpilot" or body.origin != "demo" or body.issue_number != 1:
        raise HTTPException(503, "Persisted workflows are currently limited to the bundled demo issue until user authentication and ownership are available.")
    repo = _require_repo(body.repository_id)
    issue = DEMO_ISSUES[1].copy()
    issue["origin"] = "demo"
    now = datetime.now(timezone.utc).isoformat()
    workflow = {"workflow_id": f"wf_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid4().hex[:6]}",
                "repository_id": body.repository_id, "status": "INVESTIGATING", "final_status": None,
                "issue": issue, "investigation": None, "plan": None, "patch": None, "test": None,
                "verification": None, "review": None, "approval": None, "created_at": now, "updated_at": now}
    database.save_workflow(workflow)
    try:
        workflow["investigation"] = investigate(repo, issue)
        workflow["status"] = "INVESTIGATED"
        return _save_workflow(workflow)
    except (OSError, ValueError) as exc:
        workflow["status"] = "FAILED"
        workflow["error"] = "Investigation could not read the indexed repository evidence."
        _save_workflow(workflow)
        raise HTTPException(422, workflow["error"]) from exc


@app.get("/api/workflow/{workflow_id}", response_model=WorkflowRecord)
async def get_workflow(workflow_id: str) -> WorkflowRecord:
    return WorkflowRecord.model_validate(_get_workflow(workflow_id))


@app.post("/api/workflow/{workflow_id}/plan", response_model=WorkflowRecord)
async def workflow_plan(workflow_id: str, body: WorkflowPlanRequest | None = None) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not workflow.get("investigation"):
        raise HTTPException(409, "Investigate the issue before creating a plan.")
    repo = _require_repo(workflow["repository_id"])
    requirement = (body.requirement if body else None) or workflow["issue"]["title"]
    workflow["status"] = "PLANNING"
    database.save_workflow(workflow)
    workflow["plan"] = plan_workflow(requirement, repo, workflow["investigation"])
    workflow["status"] = "PLANNED"
    database.add_activity(workflow["repository_id"], "Issue workflow plan generated", workflow_id)
    return _save_workflow(workflow)


@app.post("/api/workflow/{workflow_id}/patch", response_model=WorkflowRecord)
async def workflow_patch(workflow_id: str) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not workflow.get("plan"):
        raise HTTPException(409, "Create an implementation plan before proposing a patch.")
    repo = _require_repo(workflow["repository_id"])
    try:
        workflow["patch"] = propose_patch(repo, workflow["investigation"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    workflow["test"] = None
    workflow["approval"] = None
    workflow["verification"] = None
    workflow["review"] = None
    workflow["final_status"] = None
    workflow["status"] = "PATCH_GENERATED"
    database.add_activity(workflow["repository_id"], "Issue workflow patch proposed", workflow_id)
    return _save_workflow(workflow)


@app.post("/api/workflow/{workflow_id}/test", response_model=WorkflowRecord)
async def workflow_test(workflow_id: str) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not workflow.get("patch"):
        raise HTTPException(409, "Generate a patch proposal before drafting its regression test.")
    workflow["test"] = regression_test()
    workflow["status"] = "TEST_GENERATED"
    database.add_activity(workflow["repository_id"], "Issue workflow regression test drafted", workflow_id)
    workflow["status"] = "WAITING_FOR_APPROVAL"
    return _save_workflow(workflow)


@app.post("/api/workflow/{workflow_id}/approve", response_model=WorkflowRecord)
async def workflow_approve(workflow_id: str, body: WorkflowApprovalRequest) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not workflow.get("patch") or not workflow.get("test"):
        raise HTTPException(409, "Review the proposed patch and regression test before approving verification.")
    if not body.approved:
        workflow["approval"] = {"approved": False, "at": datetime.now(timezone.utc).isoformat()}
        workflow["status"] = "WAITING_FOR_APPROVAL"
        return _save_workflow(workflow)
    workflow["approval"] = {"approved": True, "at": datetime.now(timezone.utc).isoformat(),
                             "scope": "temporary demo workspace only"}
    workflow["status"] = "WAITING_FOR_APPROVAL"
    return _save_workflow(workflow)


@app.post("/api/workflow/{workflow_id}/reject", response_model=WorkflowRecord)
async def workflow_reject(workflow_id: str) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not workflow.get("patch"):
        raise HTTPException(409, "There is no proposed patch to reject.")
    workflow["approval"] = {"approved": False, "decision": "rejected", "at": datetime.now(timezone.utc).isoformat()}
    workflow["status"] = "REJECTED"
    workflow["final_status"] = "REJECTED"
    return _save_workflow(workflow)


@app.post("/api/workflow/{workflow_id}/verify", response_model=WorkflowRecord)
async def workflow_verify(workflow_id: str) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not (workflow.get("approval") or {}).get("approved"):
        raise HTTPException(409, "Explicit approval is required before applying the patch in a temporary verification workspace.")
    workflow["status"] = "VERIFYING"
    database.save_workflow(workflow)
    repo = _require_repo(workflow["repository_id"])
    try:
        workflow["verification"] = verify_demo(repo, workflow["patch"], workflow["test"])
        workflow["status"] = "VERIFIED" if workflow["verification"]["status"] == "PASS" else "FAILED"
    except (OSError, ValueError) as exc:
        workflow["status"] = "FAILED"
        workflow["verification"] = {"status": "ERROR", "command": "temporary demo verifier",
                                    "exit_code": None, "stdout": "", "stderr": str(exc)[:500]}
    database.add_activity(workflow["repository_id"], "Issue workflow verification " + workflow["status"].lower(), workflow_id)
    return _save_workflow(workflow)


@app.post("/api/workflow/{workflow_id}/review", response_model=WorkflowRecord)
async def workflow_review(workflow_id: str) -> WorkflowRecord:
    workflow = _get_workflow(workflow_id)
    if not workflow.get("verification"):
        raise HTTPException(409, "Verify the proposed change before requesting the final review.")
    workflow["review"] = review_workflow(workflow)
    workflow["final_status"] = workflow["review"]["status"]
    workflow["status"] = "REVIEWED"
    return _save_workflow(workflow)

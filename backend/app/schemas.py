from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    url: HttpUrl


class ChatRequest(BaseModel):
    repository_id: str
    question: str = Field(min_length=3, max_length=2000)


class GenerateRequest(BaseModel):
    repository_id: str
    target: str = Field(default="", max_length=300)
    request: str = Field(default="", max_length=2000)


class ReviewRequest(BaseModel):
    diff: str = Field(min_length=1, max_length=30000)


class PlanRequest(BaseModel):
    repository_id: str
    requirement: str = Field(min_length=5, max_length=2000)


class WorkflowInvestigationRequest(BaseModel):
    repository_id: str
    origin: Literal["demo", "github", "manual"] = "demo"
    issue_number: int | None = Field(default=None, ge=1)
    issue_title: str = Field(default="", max_length=300)
    issue_body: str = Field(default="", max_length=8000)
    stack_trace: str = Field(default="", max_length=12000)
    labels: list[str] = Field(default_factory=list, max_length=20)


class WorkflowApprovalRequest(BaseModel):
    approved: bool


class WorkflowPlanRequest(BaseModel):
    requirement: str | None = Field(default=None, max_length=2000)


class EvidenceItem(BaseModel):
    file_path: str
    symbol: str = ""
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    excerpt: str


class InvestigationResult(BaseModel):
    issue: str
    root_cause: str
    confidence: float = Field(ge=0, le=1)
    affected_files: list[str]
    affected_symbols: list[str]
    evidence: list[EvidenceItem]
    recommendations: list[str]


class WorkflowStep(BaseModel):
    step: str
    detail: str
    files_to_modify: list[str] = Field(default_factory=list)


class WorkflowRecord(BaseModel):
    workflow_id: str
    repository_id: str
    status: Literal[
        "CREATED", "INVESTIGATING", "INVESTIGATED", "PLANNING", "PLANNED",
        "PATCH_GENERATED", "TEST_GENERATED", "VERIFYING", "VERIFIED", "FAILED",
        "REVIEWED", "WAITING_FOR_APPROVAL", "REJECTED"
    ]
    final_status: str | None = None
    issue: dict
    investigation: InvestigationResult | None = None
    plan: list[WorkflowStep] | None = None
    patch: dict | None = None
    test: dict | None = None
    verification: dict | None = None
    review: dict | None = None
    approval: dict | None = None
    created_at: str
    updated_at: str

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
EventState = Literal["pending", "running", "done", "error"]


class Evidence(BaseModel):
    kind: str
    path: str
    excerpt: str


class ProposedFix(BaseModel):
    summary: str
    files: List[str] = Field(default_factory=list)


class Diagnosis(BaseModel):
    incident_id: str
    root_cause: str
    confidence: Confidence
    evidence: List[Evidence] = Field(default_factory=list)
    affected_services: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    proposed_fix: ProposedFix
    test_result: Optional[str] = None
    git_diff: Optional[str] = None


class InvestigationEvent(BaseModel):
    incident_id: str
    seq: int
    label: str
    state: EventState
    detail: Optional[str] = None
    created_at: str


ArtifactKind = Literal["change_brief", "runbook", "postmortem", "decision_brief"]


class Artifact(BaseModel):
    incident_id: str
    kind: ArtifactKind
    body: Dict[str, Any]
    created_at: str

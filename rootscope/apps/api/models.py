from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from agent.schemas import Artifact, Diagnosis, InvestigationEvent

DemoKey = Literal["contract", "config", "noisy"]
IncidentSource = Literal["demo", "freeform"]
IncidentStatus = Literal[
    "created", "investigating", "applying", "diagnosed", "fix_applied", "failed"
]


class IncidentCreate(BaseModel):
    description: str = ""
    demo_key: Optional[DemoKey] = None


class Incident(BaseModel):
    id: str
    title: str
    description: str
    source: IncidentSource
    demo_key: Optional[DemoKey] = None
    status: IncidentStatus
    created_at: datetime


class IncidentList(BaseModel):
    incidents: list[Incident] = Field(default_factory=list)


class IncidentDetail(Incident):
    events: List[InvestigationEvent] = Field(default_factory=list)
    diagnosis: Optional[Diagnosis] = None
    artifacts: List[Artifact] = Field(default_factory=list)


class DemoFixture(BaseModel):
    key: DemoKey
    title: str
    description: str
    expected_signal: str
    apply_command: str
    reset_command: str
    needs_restart: bool


class DemoCatalog(BaseModel):
    demos: list[DemoFixture]
    active: Optional[DemoKey] = None

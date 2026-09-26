from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class StageState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class WorkflowState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StageDefinition(BaseModel):
    """A stage parsed from the workflow YAML."""
    id: str
    type: str
    depends_on: list[str] = Field(default_factory=list)
    image: Optional[str] = None
    command: Optional[list[str]] = None
    env: Optional[dict[str, str]] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None
    limit_memory: Optional[str] = None  # Phase 4: K8s memory hard limit (OOMKill threshold)

class WorkflowDefinition(BaseModel):
    """Complete workflow definition parsed from YAML."""
    name: str
    stages: list[StageDefinition]
    deadline_seconds: Optional[int] = None  # Phase 4: SLA deadline for the entire workflow

class StageStatus(BaseModel):
    """Runtime status of a single stage."""
    id: str
    type: str
    state: StageState = StageState.PENDING
    job_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    prediction: Optional[dict] = None
    decision: Optional[dict] = None
    actual_metrics: Optional[dict] = None

class WorkflowStatus(BaseModel):
    """Runtime status of an entire workflow."""
    workflow_id: str
    name: str
    state: WorkflowState = WorkflowState.PENDING
    stages: dict[str, StageStatus] = Field(default_factory=dict)
    submitted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

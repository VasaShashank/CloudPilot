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
<<<<<<< HEAD
    limit_memory: Optional[str] = None
=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

class WorkflowDefinition(BaseModel):
    """Complete workflow definition parsed from YAML."""
    name: str
    stages: list[StageDefinition]
<<<<<<< HEAD
    deadline_seconds: Optional[float] = None
=======
>>>>>>> 7a9de9c1505bb7839e834f195fb148778d6108b1

class StageStatus(BaseModel):
    """Runtime status of a single stage."""
    id: str
    type: str
    state: StageState = StageState.PENDING
    job_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

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

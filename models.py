import math
from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict, Field, field_validator



class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    RUNNING = "running"
    UNKNOWN = "unknown"

_STATUS_ALIASES = {
    "success": ExecutionStatus.COMPLETED,
    "succeeded": ExecutionStatus.COMPLETED,
    "complete": ExecutionStatus.COMPLETED,
    "completed": ExecutionStatus.COMPLETED,
    "failure": ExecutionStatus.FAILED,
    "error": ExecutionStatus.FAILED,
    "failed": ExecutionStatus.FAILED,
    "running": ExecutionStatus.RUNNING,
    "in_progress": ExecutionStatus.RUNNING,
    "in-progress": ExecutionStatus.RUNNING,
    "unknown": ExecutionStatus.UNKNOWN,
}
    

class Execution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str = Field(min_length=1)
    started_at: float
    finished_at: float | None = None
    attempt: int = Field(ge=1)
    status: ExecutionStatus
    execution_duration: float | None = None

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("job_id cannot be empty or whitespace")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> ExecutionStatus:
        if isinstance(value, ExecutionStatus):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            return _STATUS_ALIASES.get(normalized, ExecutionStatus.UNKNOWN)
        return ExecutionStatus.UNKNOWN

    @field_validator("started_at", "finished_at")
    @classmethod
    def validate_finite_timestamp(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("timestamp must be a finite number")
        return value


class ExecutionSummary(BaseModel):
    total_jobs: int = Field(ge=0)
    successful_jobs: int = Field(ge=0)
    failed_jobs: int = Field(ge=0)
    avg_successful_job_duration: float = Field(default=0.0, ge=0)
    retried_jobs: int = Field(ge=0)

class JSONProcessingResult(BaseModel):
    data: List[Execution]
    validation_errors: int 
    total_records: int 

class ProcessingResponse(BaseModel):
    status: str
    summary: ExecutionSummary
    validation_errors: int 
    total_records: int

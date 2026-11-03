from typing import Any, Literal
from pydantic import BaseModel, Field

Diagnostic = Literal["system_info", "resource_usage", "disk_usage", "network_summary"]

class EnrollmentCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)

class EnrollmentResponse(BaseModel):
    code: str
    label: str
    expires_at: str

class JobCreate(BaseModel):
    device_id: str
    operation: Diagnostic
    arguments: dict[str, Any] = Field(default_factory=dict)

class AgentEnroll(BaseModel):
    code: str = Field(min_length=12, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)

class JobResult(BaseModel):
    job_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

"""Pydantic schemas for Execution API."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from agent_orchestrator.core.schemas.common import BaseSchema, PaginatedResponse
from agent_orchestrator.database.models.execution import ExecutionStatus


class ExecutionCreate(BaseModel):
    """Schema for starting a workflow execution."""

    workflow_id: UUID = Field(
        ...,
        description="ID of the workflow to execute",
    )
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for the workflow",
        examples=[{"query": "What is 2+2?", "context": "Math question"}],
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID for resuming execution (auto-generated if not provided)",
    )
    config: Optional[dict] = Field(
        default=None,
        description="Additional execution configuration",
    )


class ExecutionStepResponse(BaseSchema):
    """Schema for execution step response."""

    id: UUID
    node_id: str
    status: ExecutionStatus
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate step duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ExecutionResponse(BaseSchema):
    """Schema for execution response."""

    id: UUID
    workflow_id: UUID
    thread_id: str
    status: ExecutionStatus
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    steps: list[ExecutionStepResponse] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ExecutionListResponse(PaginatedResponse[ExecutionResponse]):
    """Paginated list of executions."""

    pass


class ExecutionStatusResponse(BaseModel):
    """Lightweight status response for polling."""

    id: UUID
    status: ExecutionStatus
    current_node: Optional[str] = None
    progress: Optional[dict] = Field(
        default=None,
        description="Progress information",
        examples=[
            {
                "total_nodes": 5,
                "completed_nodes": 2,
                "current_node": "agent_1",
                "percentage": 40,
            }
        ],
    )
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionEventData(BaseModel):
    """Data sent in SSE events during execution."""

    event_type: str = Field(
        ...,
        description="Type of event",
        examples=["node_start", "node_complete", "execution_complete", "error"],
    )
    node_id: Optional[str] = None
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

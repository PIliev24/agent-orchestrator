"""Pydantic schemas for Execution API."""

from datetime import datetime
from typing import Any
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
    thread_id: str | None = Field(
        default=None,
        description="Thread ID for resuming execution (auto-generated if not provided)",
    )
    config: dict | None = Field(
        default=None,
        description="Additional execution configuration",
    )


class ExecutionStepResponse(BaseSchema):
    """Schema for execution step response."""

    id: UUID
    node_id: str
    status: ExecutionStatus
    input_data: dict | None
    output_data: dict | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None

    @property
    def duration_seconds(self) -> float | None:
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
    input_data: dict | None
    output_data: dict | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    steps: list[ExecutionStepResponse] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ExecutionListResponse(PaginatedResponse[ExecutionResponse]):
    """Paginated list of executions."""

    pass


class ExecutionStepListResponse(PaginatedResponse[ExecutionStepResponse]):
    """Paginated list of execution steps."""

    pass


class ExecutionStatusResponse(BaseModel):
    """Lightweight status response for polling."""

    id: UUID
    status: ExecutionStatus
    current_node: str | None = None
    progress: dict | None = Field(
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
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ExecutionEventData(BaseModel):
    """Data sent in SSE events during execution."""

    event_type: str = Field(
        ...,
        description="Type of event",
        examples=["node_start", "node_complete", "execution_complete", "error"],
    )
    node_id: str | None = None
    data: dict | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

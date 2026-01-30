"""Pydantic schemas for API request/response models."""

from agent_orchestrator.core.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    ModelConfig,
)
from agent_orchestrator.core.schemas.common import (
    HealthResponse,
    PaginatedResponse,
    PaginationParams,
)
from agent_orchestrator.core.schemas.execution import (
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionStatusResponse,
    ExecutionStepResponse,
)
from agent_orchestrator.core.schemas.tool import (
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolUpdate,
)
from agent_orchestrator.core.schemas.workflow import (
    WorkflowCreate,
    WorkflowEdgeCreate,
    WorkflowListResponse,
    WorkflowNodeCreate,
    WorkflowResponse,
    WorkflowUpdate,
)

__all__ = [
    # Common
    "PaginatedResponse",
    "PaginationParams",
    "HealthResponse",
    # Agent
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentListResponse",
    "ModelConfig",
    # Tool
    "ToolCreate",
    "ToolUpdate",
    "ToolResponse",
    "ToolListResponse",
    # Workflow
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowResponse",
    "WorkflowListResponse",
    "WorkflowNodeCreate",
    "WorkflowEdgeCreate",
    # Execution
    "ExecutionCreate",
    "ExecutionResponse",
    "ExecutionListResponse",
    "ExecutionStepResponse",
    "ExecutionStatusResponse",
]

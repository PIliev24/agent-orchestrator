"""Pydantic schemas for API request/response models."""

from agent_orchestrator.core.schemas.common import (
    PaginatedResponse,
    PaginationParams,
    HealthResponse,
)
from agent_orchestrator.core.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    ModelConfig,
)
from agent_orchestrator.core.schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
)
from agent_orchestrator.core.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
)
from agent_orchestrator.core.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionStepResponse,
    ExecutionStatusResponse,
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

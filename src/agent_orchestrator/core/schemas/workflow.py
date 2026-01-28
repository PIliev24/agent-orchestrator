"""Pydantic schemas for Workflow API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from agent_orchestrator.core.schemas.common import BaseSchema, PaginatedResponse, TimestampMixin
from agent_orchestrator.database.models.workflow import NodeType


class WorkflowNodeCreate(BaseModel):
    """Schema for creating a workflow node."""

    node_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for this node within the workflow",
        examples=["agent_1", "router", "parallel_dispatch"],
    )
    node_type: NodeType = Field(
        ...,
        description="Type of node",
    )
    agent_id: Optional[UUID] = Field(
        default=None,
        description="Agent ID for AGENT nodes",
    )
    router_config: Optional[dict] = Field(
        default=None,
        description="Routing configuration for ROUTER nodes",
        examples=[
            {
                "routes": [
                    {"condition": "state.get('score', 0) > 0.8", "target": "high_quality"},
                    {"condition": "state.get('score', 0) > 0.5", "target": "medium_quality"},
                ],
                "default": "low_quality",
            }
        ],
    )
    parallel_nodes: Optional[list[str]] = Field(
        default=None,
        description="List of node IDs for PARALLEL nodes",
    )
    subgraph_workflow_id: Optional[UUID] = Field(
        default=None,
        description="Workflow ID for SUBGRAPH nodes",
    )
    config: Optional[dict] = Field(
        default=None,
        description="Additional node configuration",
    )


class WorkflowNodeResponse(BaseSchema):
    """Schema for workflow node response."""

    id: UUID
    node_id: str
    node_type: NodeType
    agent_id: Optional[UUID]
    router_config: Optional[dict]
    parallel_nodes: Optional[list[str]]
    subgraph_workflow_id: Optional[UUID]
    config: Optional[dict]


class WorkflowEdgeCreate(BaseModel):
    """Schema for creating a workflow edge."""

    source_node: str = Field(
        ...,
        description="Source node ID (use '__start__' for START)",
        examples=["__start__", "agent_1"],
    )
    target_node: str = Field(
        ...,
        description="Target node ID (use '__end__' for END)",
        examples=["agent_1", "__end__"],
    )
    condition: Optional[str] = Field(
        default=None,
        description="Python expression for conditional edge (evaluated against state)",
        examples=["state.get('approved', False) == True"],
    )


class WorkflowEdgeResponse(BaseSchema):
    """Schema for workflow edge response."""

    id: UUID
    source_node: str
    target_node: str
    condition: Optional[str]


class WorkflowCreate(BaseModel):
    """Schema for creating a new workflow."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Workflow name",
        examples=["Question Generation Pipeline"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Workflow description",
    )
    state_schema: Optional[dict] = Field(
        default=None,
        description="JSON Schema for workflow state",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional workflow metadata",
    )
    is_template: bool = Field(
        default=False,
        description="Whether this is a template workflow",
    )
    nodes: list[WorkflowNodeCreate] = Field(
        ...,
        min_length=1,
        description="List of workflow nodes",
    )
    edges: list[WorkflowEdgeCreate] = Field(
        ...,
        min_length=1,
        description="List of workflow edges",
    )


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    description: Optional[str] = None
    state_schema: Optional[dict] = None
    metadata: Optional[dict] = None
    is_template: Optional[bool] = None
    nodes: Optional[list[WorkflowNodeCreate]] = None
    edges: Optional[list[WorkflowEdgeCreate]] = None


class WorkflowResponse(BaseSchema, TimestampMixin):
    """Schema for workflow response."""

    id: UUID
    name: str
    description: Optional[str]
    state_schema: Optional[dict]
    metadata: Optional[dict]
    is_template: bool
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]


class WorkflowListResponse(PaginatedResponse[WorkflowResponse]):
    """Paginated list of workflows."""

    pass


class WorkflowSummaryResponse(BaseSchema, TimestampMixin):
    """Summary response for workflow listing (without nodes/edges)."""

    id: UUID
    name: str
    description: Optional[str]
    is_template: bool
    node_count: int = 0
    edge_count: int = 0

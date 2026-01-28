"""Workflow service for CRUD operations."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_orchestrator.core.exceptions import (
    AgentNotFoundError,
    ValidationError,
    WorkflowNotFoundError,
)
from agent_orchestrator.core.schemas.workflow import (
    WorkflowCreate,
    WorkflowEdgeResponse,
    WorkflowNodeResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from agent_orchestrator.database.models.agent import Agent
from agent_orchestrator.database.models.workflow import (
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)


class WorkflowService:
    """Service for managing workflows."""

    def __init__(self, session: AsyncSession):
        """Initialize the service.

        Args:
            session: Database session.
        """
        self._session = session

    async def create(self, data: WorkflowCreate) -> WorkflowResponse:
        """Create a new workflow.

        Args:
            data: Workflow creation data.

        Returns:
            Created workflow response.

        Raises:
            ValidationError: If workflow structure is invalid.
            AgentNotFoundError: If any agent_id is invalid.
        """
        # Validate workflow structure
        await self._validate_workflow(data)

        # Create workflow
        workflow = Workflow(
            name=data.name,
            description=data.description,
            state_schema=data.state_schema,
            workflow_metadata=data.metadata,
            is_template=data.is_template,
        )
        self._session.add(workflow)
        await self._session.flush()

        # Add nodes
        for node_data in data.nodes:
            node = WorkflowNode(
                workflow_id=workflow.id,
                node_id=node_data.node_id,
                node_type=node_data.node_type,
                agent_id=node_data.agent_id,
                router_config=node_data.router_config,
                parallel_nodes=node_data.parallel_nodes,
                subgraph_workflow_id=node_data.subgraph_workflow_id,
                config=node_data.config,
            )
            self._session.add(node)

        # Add edges
        for edge_data in data.edges:
            edge = WorkflowEdge(
                workflow_id=workflow.id,
                source_node=edge_data.source_node,
                target_node=edge_data.target_node,
                condition=edge_data.condition,
            )
            self._session.add(edge)

        await self._session.flush()

        # Reload with relationships
        return await self.get(workflow.id)

    async def get(self, workflow_id: UUID) -> WorkflowResponse:
        """Get a workflow by ID.

        Args:
            workflow_id: Workflow ID.

        Returns:
            Workflow response.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        workflow = await self._get_workflow(workflow_id)
        return self._to_response(workflow)

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        templates_only: bool = False,
    ) -> tuple[list[WorkflowResponse], int]:
        """List workflows with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            search: Optional search term for name.
            templates_only: If True, only return template workflows.

        Returns:
            Tuple of (workflows list, total count).
        """
        query = select(Workflow).options(
            selectinload(Workflow.nodes),
            selectinload(Workflow.edges),
        )

        if search:
            query = query.where(Workflow.name.ilike(f"%{search}%"))

        if templates_only:
            query = query.where(Workflow.is_template == True)

        # Get total count
        count_query = select(func.count()).select_from(Workflow)
        if search:
            count_query = count_query.where(Workflow.name.ilike(f"%{search}%"))
        if templates_only:
            count_query = count_query.where(Workflow.is_template == True)
        total = await self._session.scalar(count_query)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Workflow.created_at.desc())

        result = await self._session.execute(query)
        workflows = result.scalars().all()

        return [self._to_response(w) for w in workflows], total or 0

    async def update(self, workflow_id: UUID, data: WorkflowUpdate) -> WorkflowResponse:
        """Update a workflow.

        Args:
            workflow_id: Workflow ID.
            data: Update data.

        Returns:
            Updated workflow response.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
            ValidationError: If new structure is invalid.
        """
        workflow = await self._get_workflow(workflow_id)

        # Update basic fields
        if data.name is not None:
            workflow.name = data.name
        if data.description is not None:
            workflow.description = data.description
        if data.state_schema is not None:
            workflow.state_schema = data.state_schema
        if data.metadata is not None:
            workflow.workflow_metadata = data.metadata
        if data.is_template is not None:
            workflow.is_template = data.is_template

        # Update nodes and edges if provided
        if data.nodes is not None or data.edges is not None:
            # Create a temporary WorkflowCreate for validation
            validate_data = WorkflowCreate(
                name=workflow.name,
                nodes=data.nodes or [
                    self._node_to_create(n) for n in workflow.nodes
                ],
                edges=data.edges or [
                    self._edge_to_create(e) for e in workflow.edges
                ],
            )
            await self._validate_workflow(validate_data)

            # Remove existing nodes and edges
            if data.nodes is not None:
                for node in workflow.nodes:
                    await self._session.delete(node)

                for node_data in data.nodes:
                    node = WorkflowNode(
                        workflow_id=workflow.id,
                        node_id=node_data.node_id,
                        node_type=node_data.node_type,
                        agent_id=node_data.agent_id,
                        router_config=node_data.router_config,
                        parallel_nodes=node_data.parallel_nodes,
                        subgraph_workflow_id=node_data.subgraph_workflow_id,
                        config=node_data.config,
                    )
                    self._session.add(node)

            if data.edges is not None:
                for edge in workflow.edges:
                    await self._session.delete(edge)

                for edge_data in data.edges:
                    edge = WorkflowEdge(
                        workflow_id=workflow.id,
                        source_node=edge_data.source_node,
                        target_node=edge_data.target_node,
                        condition=edge_data.condition,
                    )
                    self._session.add(edge)

        await self._session.flush()

        # Reload with relationships
        return await self.get(workflow.id)

    async def delete(self, workflow_id: UUID) -> None:
        """Delete a workflow.

        Args:
            workflow_id: Workflow ID.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        workflow = await self._get_workflow(workflow_id)
        await self._session.delete(workflow)

    async def clone(self, workflow_id: UUID, new_name: str) -> WorkflowResponse:
        """Clone a workflow.

        Args:
            workflow_id: Workflow ID to clone.
            new_name: Name for the cloned workflow.

        Returns:
            Cloned workflow response.
        """
        original = await self._get_workflow(workflow_id)

        # Create new workflow
        cloned = Workflow(
            name=new_name,
            description=original.description,
            state_schema=original.state_schema,
            workflow_metadata=original.workflow_metadata,
            is_template=False,  # Cloned workflows are not templates
        )
        self._session.add(cloned)
        await self._session.flush()

        # Clone nodes
        for node in original.nodes:
            new_node = WorkflowNode(
                workflow_id=cloned.id,
                node_id=node.node_id,
                node_type=node.node_type,
                agent_id=node.agent_id,
                router_config=node.router_config,
                parallel_nodes=node.parallel_nodes,
                subgraph_workflow_id=node.subgraph_workflow_id,
                config=node.config,
            )
            self._session.add(new_node)

        # Clone edges
        for edge in original.edges:
            new_edge = WorkflowEdge(
                workflow_id=cloned.id,
                source_node=edge.source_node,
                target_node=edge.target_node,
                condition=edge.condition,
            )
            self._session.add(new_edge)

        await self._session.flush()

        return await self.get(cloned.id)

    async def _get_workflow(self, workflow_id: UUID) -> Workflow:
        """Get a workflow by ID or raise error.

        Args:
            workflow_id: Workflow ID.

        Returns:
            Workflow model.

        Raises:
            WorkflowNotFoundError: If not found.
        """
        query = (
            select(Workflow)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
            .where(Workflow.id == workflow_id)
        )
        result = await self._session.execute(query)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise WorkflowNotFoundError(workflow_id)

        return workflow

    async def _validate_workflow(self, data: WorkflowCreate) -> None:
        """Validate workflow structure.

        Args:
            data: Workflow data to validate.

        Raises:
            ValidationError: If structure is invalid.
            AgentNotFoundError: If agent IDs are invalid.
        """
        # Collect all node IDs
        node_ids = {node.node_id for node in data.nodes}

        # Check for duplicate node IDs
        if len(node_ids) != len(data.nodes):
            raise ValidationError("Duplicate node IDs found")

        # Validate edges reference valid nodes
        for edge in data.edges:
            if edge.source_node not in ("__start__",) and edge.source_node not in node_ids:
                raise ValidationError(
                    f"Edge source '{edge.source_node}' references unknown node"
                )
            if edge.target_node not in ("__end__",) and edge.target_node not in node_ids:
                raise ValidationError(
                    f"Edge target '{edge.target_node}' references unknown node"
                )

        # Validate agent IDs exist
        agent_ids = [
            node.agent_id for node in data.nodes
            if node.agent_id is not None
        ]
        if agent_ids:
            count = await self._session.scalar(
                select(func.count()).select_from(Agent).where(Agent.id.in_(agent_ids))
            )
            if count != len(agent_ids):
                raise AgentNotFoundError(
                    str(agent_ids),
                    "One or more agent IDs are invalid",
                )

    def _to_response(self, workflow: Workflow) -> WorkflowResponse:
        """Convert Workflow model to response schema.

        Args:
            workflow: Workflow model.

        Returns:
            WorkflowResponse schema.
        """
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            state_schema=workflow.state_schema,
            metadata=workflow.workflow_metadata,
            is_template=workflow.is_template,
            nodes=[
                WorkflowNodeResponse(
                    id=n.id,
                    node_id=n.node_id,
                    node_type=n.node_type,
                    agent_id=n.agent_id,
                    router_config=n.router_config,
                    parallel_nodes=n.parallel_nodes,
                    subgraph_workflow_id=n.subgraph_workflow_id,
                    config=n.config,
                )
                for n in workflow.nodes
            ],
            edges=[
                WorkflowEdgeResponse(
                    id=e.id,
                    source_node=e.source_node,
                    target_node=e.target_node,
                    condition=e.condition,
                )
                for e in workflow.edges
            ],
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    def _node_to_create(self, node: WorkflowNode):
        """Convert WorkflowNode to WorkflowNodeCreate."""
        from agent_orchestrator.core.schemas.workflow import WorkflowNodeCreate
        return WorkflowNodeCreate(
            node_id=node.node_id,
            node_type=node.node_type,
            agent_id=node.agent_id,
            router_config=node.router_config,
            parallel_nodes=node.parallel_nodes,
            subgraph_workflow_id=node.subgraph_workflow_id,
            config=node.config,
        )

    def _edge_to_create(self, edge: WorkflowEdge):
        """Convert WorkflowEdge to WorkflowEdgeCreate."""
        from agent_orchestrator.core.schemas.workflow import WorkflowEdgeCreate
        return WorkflowEdgeCreate(
            source_node=edge.source_node,
            target_node=edge.target_node,
            condition=edge.condition,
        )

"""Workflow compiler that converts database models to LangGraph StateGraphs."""

from typing import Any, Callable, Optional
from uuid import UUID

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from agent_orchestrator.core.exceptions import WorkflowCompilationError, WorkflowNotFoundError
from agent_orchestrator.database.models.workflow import NodeType, Workflow, WorkflowNode
from agent_orchestrator.database.models.agent import Agent, AgentTool
from agent_orchestrator.tools.registry import ToolRegistry
from agent_orchestrator.workflows.checkpointer import get_checkpointer
from agent_orchestrator.workflows.nodes.agent_node import create_agent_node_sync
from agent_orchestrator.workflows.nodes.parallel_node import create_join_node, create_parallel_node
from agent_orchestrator.workflows.nodes.router_node import create_conditional_edges
from agent_orchestrator.workflows.state import WorkflowState, create_state_class


class WorkflowCompiler:
    """Compiles workflow database models into executable LangGraph graphs."""

    def __init__(self, session: AsyncSession):
        """Initialize the compiler.

        Args:
            session: Database session for loading workflows and agents.
        """
        self._session = session

    async def compile(
        self,
        workflow_id: UUID,
        checkpointer: Optional[AsyncPostgresSaver] = None,
    ) -> CompiledStateGraph:
        """Compile a workflow into a LangGraph StateGraph.

        Args:
            workflow_id: ID of the workflow to compile.
            checkpointer: Optional checkpointer for state persistence.
                If None, uses the default PostgreSQL checkpointer.

        Returns:
            Compiled StateGraph ready for execution.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
            WorkflowCompilationError: If compilation fails.
        """
        # Load workflow with nodes and edges
        workflow = await self._load_workflow(workflow_id)

        # Get or create checkpointer
        if checkpointer is None:
            checkpointer = await get_checkpointer()

        try:
            return await self._compile_workflow(workflow, checkpointer)
        except Exception as e:
            raise WorkflowCompilationError(
                workflow_id=workflow_id,
                message=f"Failed to compile workflow: {e}",
            )

    async def _load_workflow(self, workflow_id: UUID) -> Workflow:
        """Load a workflow with all its nodes and edges.

        Args:
            workflow_id: Workflow ID.

        Returns:
            Loaded Workflow model.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        stmt = (
            select(Workflow)
            .options(
                selectinload(Workflow.nodes)
                .selectinload(WorkflowNode.agent)
                .selectinload(Agent.agent_tools)
                .selectinload(AgentTool.tool),
                selectinload(Workflow.edges),
            )
            .where(Workflow.id == workflow_id)
        )
        result = await self._session.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise WorkflowNotFoundError(workflow_id)

        return workflow

    async def _compile_workflow(
        self,
        workflow: Workflow,
        checkpointer: AsyncPostgresSaver,
    ) -> CompiledStateGraph:
        """Compile a loaded workflow into a StateGraph.

        Args:
            workflow: Loaded Workflow model.
            checkpointer: Checkpointer for state persistence.

        Returns:
            Compiled StateGraph.
        """
        # Create state class from schema
        StateClass = create_state_class(workflow.state_schema)

        # Build the graph
        builder = StateGraph(StateClass)

        # Create a map of node_id -> node for easy lookup
        nodes_map = {node.node_id: node for node in workflow.nodes}

        # Add nodes
        for node in workflow.nodes:
            node_func = await self._create_node_function(node)
            builder.add_node(node.node_id, node_func)

        # Add edges
        await self._add_edges(builder, workflow, nodes_map)

        # Compile with checkpointer
        return builder.compile(checkpointer=checkpointer)

    async def _create_node_function(
        self,
        node: WorkflowNode,
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Create the appropriate node function based on node type.

        Args:
            node: WorkflowNode model.

        Returns:
            Async function for the node.

        Raises:
            WorkflowCompilationError: If node type is not supported.
        """
        match node.node_type:
            case NodeType.AGENT:
                return await self._create_agent_node(node)

            case NodeType.ROUTER:
                # Router nodes return a string (target node), not a dict
                # They're handled via conditional edges
                return self._create_passthrough_node(node.node_id)

            case NodeType.PARALLEL:
                return create_parallel_node(
                    node.parallel_nodes or [],
                    node.config.get("fan_out_key") if node.config else None,
                )

            case NodeType.JOIN:
                config = node.config or {}
                return create_join_node(
                    aggregation_strategy=config.get("strategy", "merge"),
                    output_key=config.get("output_key", "parallel_results"),
                )

            case NodeType.SUBGRAPH:
                return await self._create_subgraph_node(node)

            case _:
                raise WorkflowCompilationError(
                    workflow_id=node.workflow_id,
                    node_id=node.node_id,
                    message=f"Unsupported node type: {node.node_type}",
                )

    async def _create_agent_node(
        self,
        node: WorkflowNode,
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Create an agent node function.

        Args:
            node: WorkflowNode with agent_id set.

        Returns:
            Async function that executes the agent.
        """
        if not node.agent_id:
            raise WorkflowCompilationError(
                workflow_id=node.workflow_id,
                node_id=node.node_id,
                message="Agent node missing agent_id",
            )

        # Agent should be loaded via relationship
        agent = node.agent
        if not agent:
            # Try loading directly
            agent = await self._session.get(Agent, node.agent_id)
            if not agent:
                raise WorkflowCompilationError(
                    workflow_id=node.workflow_id,
                    node_id=node.node_id,
                    message=f"Agent {node.agent_id} not found",
                )

        # Load tools for the agent
        tools = []
        for agent_tool in agent.agent_tools:
            tool = agent_tool.tool
            try:
                lc_tool = ToolRegistry.get_langchain_tool(
                    tool.implementation_ref,
                    tool.config,
                )
                tools.append(lc_tool)
            except Exception:
                # Skip tools that fail to load
                pass

        return create_agent_node_sync(agent, tools)

    def _create_passthrough_node(
        self,
        node_id: str,
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Create a passthrough node that just updates current_node.

        Args:
            node_id: Node identifier.

        Returns:
            Passthrough function.
        """

        async def passthrough(state: dict[str, Any]) -> dict[str, Any]:
            return {"current_node": node_id}

        return passthrough

    async def _create_subgraph_node(
        self,
        node: WorkflowNode,
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Create a subgraph node that executes another workflow.

        Args:
            node: WorkflowNode with subgraph_workflow_id set.

        Returns:
            Async function that executes the subgraph.
        """
        if not node.subgraph_workflow_id:
            raise WorkflowCompilationError(
                workflow_id=node.workflow_id,
                node_id=node.node_id,
                message="Subgraph node missing subgraph_workflow_id",
            )

        # Compile the subgraph workflow
        subgraph = await self.compile(node.subgraph_workflow_id)

        async def subgraph_executor(state: dict[str, Any]) -> dict[str, Any]:
            """Execute the subgraph workflow.

            Args:
                state: Current workflow state.

            Returns:
                Updated state with subgraph output.
            """
            # Execute subgraph with current state as input
            config = {"configurable": {"thread_id": f"subgraph_{node.node_id}"}}
            result = await subgraph.ainvoke(state, config)

            # Merge subgraph output into state
            return {
                "current_node": node.node_id,
                "intermediate": {
                    **state.get("intermediate", {}),
                    node.node_id: result.get("output"),
                },
                "output": result.get("output"),
            }

        return subgraph_executor

    async def _add_edges(
        self,
        builder: StateGraph,
        workflow: Workflow,
        nodes_map: dict[str, WorkflowNode],
    ) -> None:
        """Add edges to the graph builder.

        Args:
            builder: StateGraph builder.
            workflow: Workflow model.
            nodes_map: Map of node_id to WorkflowNode.
        """
        # Group edges by source for conditional edge detection
        edges_by_source: dict[str, list] = {}
        for edge in workflow.edges:
            if edge.source_node not in edges_by_source:
                edges_by_source[edge.source_node] = []
            edges_by_source[edge.source_node].append(edge)

        for source, edges in edges_by_source.items():
            # Convert special node names
            source_node = START if source == "__start__" else source

            # Check if any edges have conditions
            has_conditions = any(e.condition for e in edges)

            if has_conditions or len(edges) > 1:
                # Use conditional edges
                await self._add_conditional_edges(builder, source_node, edges, nodes_map)
            else:
                # Simple direct edge
                edge = edges[0]
                target_node = END if edge.target_node == "__end__" else edge.target_node
                builder.add_edge(source_node, target_node)

    async def _add_conditional_edges(
        self,
        builder: StateGraph,
        source_node: str,
        edges: list,
        nodes_map: dict[str, WorkflowNode],
    ) -> None:
        """Add conditional edges to the graph.

        Args:
            builder: StateGraph builder.
            source_node: Source node name (or START).
            edges: List of edges from this source.
            nodes_map: Map of node_id to WorkflowNode.
        """
        # Check if source is a router node
        if source_node != START and source_node in nodes_map:
            node = nodes_map[source_node]
            if node.node_type == NodeType.ROUTER and node.router_config:
                # Use router config for conditional edges
                router_func, path_map = create_conditional_edges(node.router_config)
                builder.add_conditional_edges(source_node, router_func, path_map)
                return

        # Build conditional routing from edge conditions
        conditions = []
        default_target = END

        for edge in edges:
            target = END if edge.target_node == "__end__" else edge.target_node

            if edge.condition:
                conditions.append({
                    "condition": edge.condition,
                    "target": target,
                })
            else:
                # Edge without condition is the default
                default_target = target

        if conditions:
            router_config = {
                "routes": conditions,
                "default": default_target,
            }
            router_func, path_map = create_conditional_edges(router_config)
            builder.add_conditional_edges(source_node, router_func, path_map)
        else:
            # No conditions, just add direct edge to default
            builder.add_edge(source_node, default_target)

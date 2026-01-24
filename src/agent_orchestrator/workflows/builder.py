"""Main workflow builder for LangGraph."""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent_orchestrator.agents.executor import AgentExecutor
from agent_orchestrator.core.schemas.agent import AgentConfig
from agent_orchestrator.core.schemas.workflow import (
    WorkflowConfig,
    WorkflowEdge,
    WorkflowNode,
    WorkflowNodeType,
)
from agent_orchestrator.sessions.manager import SessionManager
from agent_orchestrator.workflows.patterns.dag import create_condition_router
from agent_orchestrator.workflows.patterns.parallel import create_aggregator
from agent_orchestrator.workflows.state import create_state_class


class WorkflowBuilder:
    """Builds LangGraph workflows from API configuration."""

    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager
        self._agent_executor = AgentExecutor(session_manager)

    def build(self, config: WorkflowConfig) -> CompiledStateGraph:
        """Build a compiled LangGraph from workflow configuration.

        Args:
            config: Workflow configuration.

        Returns:
            Compiled LangGraph ready for execution.
        """
        State = create_state_class(config.state_schema)
        builder = StateGraph(State)

        for node in config.nodes:
            node_func = self._create_node_function(node)
            builder.add_node(node.id, node_func)

        edge_sources: set[str] = set()
        for edge in config.edges:
            edge_sources.add(edge.source)

        for edge in config.edges:
            source = START if edge.source == "__start__" else edge.source
            target = END if edge.target == "__end__" else edge.target

            if edge.condition:
                condition_func = create_condition_router(edge.condition)
                builder.add_conditional_edges(source, condition_func, {edge.target: target})
            else:
                builder.add_edge(source, target)

        return builder.compile()

    def _create_node_function(self, node: WorkflowNode) -> Callable[..., dict[str, Any]]:
        """Create a node function based on node type."""
        match node.type:
            case WorkflowNodeType.AGENT:
                return self._create_agent_node(node)
            case WorkflowNodeType.CONDITIONAL:
                return self._create_conditional_node(node)
            case WorkflowNodeType.PARALLEL:
                return self._create_parallel_node(node)
            case WorkflowNodeType.AGGREGATOR:
                return self._create_aggregator_node(node)
            case _:
                raise ValueError(f"Unknown node type: {node.type}")

    def _create_agent_node(self, node: WorkflowNode) -> Callable[..., dict[str, Any]]:
        """Create an agent execution node."""
        agent_config = node.agent_config

        async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
            if not agent_config:
                return {f"{node.id}_output": None}

            user_input = state.get("input", "")
            if isinstance(user_input, dict):
                user_input = str(user_input)

            result = await self._agent_executor.execute(
                agent_config=agent_config,
                user_input=user_input,
                context=state,
            )

            return {
                f"{node.id}_output": result.output,
                "messages": [{"role": "assistant", "content": str(result.output), "node": node.id}],
            }

        return agent_node

    def _create_conditional_node(self, node: WorkflowNode) -> Callable[..., dict[str, Any]]:
        """Create a conditional routing node."""

        async def conditional_node(state: dict[str, Any]) -> dict[str, Any]:
            if not node.routes:
                return {"route": node.default_route or "__end__"}

            for route in node.routes:
                try:
                    result = eval(route.condition, {"__builtins__": {}}, {"state": state})
                    if result:
                        return {"route": route.target_node}
                except Exception:
                    continue

            return {"route": node.default_route or "__end__"}

        return conditional_node

    def _create_parallel_node(self, node: WorkflowNode) -> Callable[..., dict[str, Any]]:
        """Create a parallel execution marker node."""

        async def parallel_node(state: dict[str, Any]) -> dict[str, Any]:
            return {"parallel_nodes": node.parallel_nodes or []}

        return parallel_node

    def _create_aggregator_node(self, node: WorkflowNode) -> Callable[..., dict[str, Any]]:
        """Create an aggregator node."""
        strategy = node.aggregation_strategy or "merge"
        aggregator = create_aggregator(strategy)
        return aggregator

"""Parallel execution workflow pattern."""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from agent_orchestrator.core.schemas.agent import AgentConfig


def build_parallel_workflow(
    parallel_agents: list[AgentConfig],
    aggregator: Callable[[dict[str, Any]], dict[str, Any]],
    state_class: type,
    create_agent_node: Callable[[AgentConfig], Callable[..., dict[str, Any]]],
) -> StateGraph:
    """Build a parallel execution workflow with aggregation.

    Args:
        parallel_agents: List of agents to execute in parallel.
        aggregator: Function to aggregate parallel results.
        state_class: The state TypedDict class.
        create_agent_node: Function to create agent node from config.

    Returns:
        Compiled StateGraph for the parallel workflow.
    """
    builder = StateGraph(state_class)

    for i, agent in enumerate(parallel_agents):
        node_id = f"parallel_{i}"
        builder.add_node(node_id, create_agent_node(agent))
        builder.add_edge(START, node_id)

    builder.add_node("aggregator", aggregator)

    for i in range(len(parallel_agents)):
        builder.add_edge(f"parallel_{i}", "aggregator")

    builder.add_edge("aggregator", END)

    return builder.compile()


def create_aggregator(strategy: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an aggregator function based on strategy.

    Args:
        strategy: Aggregation strategy ("merge", "concat", or "first").

    Returns:
        An aggregator function.
    """

    async def merge_aggregator(state: dict[str, Any]) -> dict[str, Any]:
        """Merge all parallel outputs into combined result."""
        combined = {}
        for key, value in state.items():
            if key.startswith("parallel_") and key.endswith("_output"):
                combined[key] = value
        return {"aggregated_output": combined}

    async def concat_aggregator(state: dict[str, Any]) -> dict[str, Any]:
        """Concatenate all parallel outputs."""
        parts = []
        for key, value in sorted(state.items()):
            if key.startswith("parallel_") and key.endswith("_output"):
                parts.append(str(value))
        return {"aggregated_output": "\n\n".join(parts)}

    async def first_aggregator(state: dict[str, Any]) -> dict[str, Any]:
        """Return first parallel output."""
        for key, value in state.items():
            if key.startswith("parallel_") and key.endswith("_output"):
                return {"aggregated_output": value}
        return {"aggregated_output": None}

    strategies = {
        "merge": merge_aggregator,
        "concat": concat_aggregator,
        "first": first_aggregator,
    }

    return strategies.get(strategy, merge_aggregator)

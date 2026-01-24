"""Sequential chain workflow pattern."""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from agent_orchestrator.core.schemas.agent import AgentConfig


def build_sequential_chain(
    agents: list[AgentConfig],
    state_class: type,
    create_agent_node: Callable[[AgentConfig], Callable[..., dict[str, Any]]],
) -> StateGraph:
    """Build a sequential chain: A -> B -> C.

    Args:
        agents: List of agent configurations in execution order.
        state_class: The state TypedDict class.
        create_agent_node: Function to create agent node from config.

    Returns:
        Compiled StateGraph for the sequential chain.
    """
    builder = StateGraph(state_class)

    previous_node = START
    for i, agent in enumerate(agents):
        node_id = f"agent_{i}"
        builder.add_node(node_id, create_agent_node(agent))
        builder.add_edge(previous_node, node_id)
        previous_node = node_id

    builder.add_edge(previous_node, END)

    return builder.compile()

"""Conditional and loop workflow patterns."""

from typing import Any, Callable, Literal

from langgraph.graph import END, START, StateGraph

from agent_orchestrator.core.schemas.agent import AgentConfig


def build_loop_workflow(
    main_agent: AgentConfig,
    evaluator_agent: AgentConfig,
    max_iterations: int,
    state_class: type,
    create_agent_node: Callable[[AgentConfig], Callable[..., dict[str, Any]]],
) -> StateGraph:
    """Build a workflow with evaluation loop.

    Pattern: START -> main -> evaluator -> counter -> (condition) -> main or END

    Args:
        main_agent: Main processing agent configuration.
        evaluator_agent: Evaluator agent configuration.
        max_iterations: Maximum number of loop iterations.
        state_class: The state TypedDict class.
        create_agent_node: Function to create agent node from config.

    Returns:
        Compiled StateGraph for the loop workflow.
    """
    builder = StateGraph(state_class)

    builder.add_node("main", create_agent_node(main_agent))
    builder.add_node("evaluator", create_agent_node(evaluator_agent))

    async def increment_counter(state: dict[str, Any]) -> dict[str, Any]:
        return {"iteration": state.get("iteration", 0) + 1}

    builder.add_node("counter", increment_counter)

    def should_continue(state: dict[str, Any]) -> Literal["main", "__end__"]:
        if state.get("iteration", 0) >= max_iterations:
            return "__end__"
        if state.get("evaluation_passed", False):
            return "__end__"
        return "main"

    builder.add_edge(START, "main")
    builder.add_edge("main", "evaluator")
    builder.add_edge("evaluator", "counter")
    builder.add_conditional_edges(
        "counter",
        should_continue,
        {"main": "main", "__end__": END},
    )

    return builder.compile()


def build_conditional_branch_workflow(
    condition_node: Callable[[dict[str, Any]], dict[str, Any]],
    branches: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
    condition_func: Callable[[dict[str, Any]], str],
    state_class: type,
) -> StateGraph:
    """Build a workflow with conditional branching.

    Pattern: START -> condition -> (branch_a | branch_b | ...) -> END

    Args:
        condition_node: Node that evaluates the condition.
        branches: Dictionary mapping branch keys to node functions.
        condition_func: Function that returns branch key based on state.
        state_class: The state TypedDict class.

    Returns:
        Compiled StateGraph for the conditional branch workflow.
    """
    builder = StateGraph(state_class)

    builder.add_node("condition", condition_node)
    builder.add_edge(START, "condition")

    route_map = {}
    for branch_key, branch_func in branches.items():
        builder.add_node(branch_key, branch_func)
        builder.add_edge(branch_key, END)
        route_map[branch_key] = branch_key

    builder.add_conditional_edges("condition", condition_func, route_map)

    return builder.compile()

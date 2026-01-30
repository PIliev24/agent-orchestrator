"""Agent node implementation."""

import json
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10
MAX_TOOL_OUTPUT_CHARS = 180_000  # ~50-60k tokens for multilingual content

from agent_orchestrator.database.models.agent import Agent
from agent_orchestrator.providers.base import ProviderConfig
from agent_orchestrator.providers.factory import ProviderFactory
from agent_orchestrator.tools.registry import ToolRegistry


def _build_context_message(state: dict[str, Any]) -> str:
    """Build context string from workflow state input and intermediate results."""
    context_parts = []

    input_data = state.get("input", {})
    if isinstance(input_data, dict) and input_data:
        context_parts.append("## Input\n" + "\n".join(f"{k}: {v}" for k, v in input_data.items()))
    elif isinstance(input_data, str) and input_data.strip():
        context_parts.append(f"## Input\n{input_data}")

    intermediate = state.get("intermediate", {})
    if intermediate:
        for node_name, node_output in intermediate.items():
            output_str = str(node_output) if node_output else ""
            if output_str.strip():
                if len(output_str) > MAX_TOOL_OUTPUT_CHARS:
                    output_str = (
                        output_str[:MAX_TOOL_OUTPUT_CHARS]
                        + f"\n[TRUNCATED - {len(output_str)} chars total]"
                    )
                context_parts.append(f"## Output from {node_name}\n{output_str}")

    # Include parallel item context if this is a fan-out invocation
    parallel_item = state.get("parallel_item")
    if parallel_item is None:
        metadata = state.get("metadata", {})
        if isinstance(metadata, dict):
            parallel_item = metadata.get("parallel_item")
            if parallel_item is not None and "parallel_index" not in state:
                state["parallel_index"] = metadata.get("parallel_index", 0)
    if parallel_item is not None:
        parallel_index = state.get("parallel_index", 0)
        item_str = (
            json.dumps(parallel_item, ensure_ascii=False, indent=2)
            if isinstance(parallel_item, (dict, list))
            else str(parallel_item)
        )
        context_parts.append(
            f"## Current Task (Item {parallel_index + 1})\n{item_str}"
        )

    return "\n\n".join(context_parts) if context_parts else "Execute your task."


async def _run_tool_loop(
    model: Any,
    messages: list,
    tools_by_name: dict[str, Any],
) -> Any:
    """Invoke the model and handle tool-calling loop."""
    response = await model.ainvoke(messages)

    for _ in range(MAX_TOOL_ITERATIONS):
        if not (isinstance(response, AIMessage) and response.tool_calls):
            break
        messages.append(response)
        tool_messages = await _execute_tool_calls(response, tools_by_name)
        messages.extend(tool_messages)
        response = await model.ainvoke(messages)

    return response


def _extract_output(response: Any) -> Any:
    """Extract output content from a model response."""
    if hasattr(response, "content"):
        return response.content
    return response


def _build_state_updates(state: dict[str, Any], agent_name: str, output: Any) -> dict[str, Any]:
    """Build state update dict from agent output."""
    intermediate = state.get("intermediate", {})
    intermediate[agent_name] = output
    return {
        "current_node": agent_name,
        "intermediate": intermediate,
        "output": output,
    }


def _create_model(
    provider_config: ProviderConfig,
    tools: list | None,
    output_schema: dict | None,
) -> Any:
    """Create the appropriate model based on output_schema and tools."""
    if output_schema:
        return ProviderFactory.create_model(provider_config, output_schema=output_schema)
    elif tools:
        return ProviderFactory.create_model(provider_config, tools=tools)
    else:
        return ProviderFactory.create_model(provider_config)


async def _execute_tool_calls(
    response: AIMessage, tools_by_name: dict[str, Any]
) -> list[ToolMessage]:
    """Execute tool calls from an AI response and return ToolMessages."""
    tool_messages = []
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        lc_tool = tools_by_name.get(tool_name)
        if lc_tool:
            try:
                result = await lc_tool.ainvoke(tool_args)
                content = str(result) if result is not None else ""
                if len(content) > MAX_TOOL_OUTPUT_CHARS:
                    logger.warning(
                        "Tool %s output truncated from %d to %d chars",
                        tool_name,
                        len(content),
                        MAX_TOOL_OUTPUT_CHARS,
                    )
                    content = (
                        content[:MAX_TOOL_OUTPUT_CHARS]
                        + f"\n\n[OUTPUT TRUNCATED - showed {MAX_TOOL_OUTPUT_CHARS} of {len(content)} chars]"
                    )
            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                content = f"Error executing tool {tool_name}: {e}"
        else:
            content = f"Tool {tool_name} not found."
        tool_messages.append(ToolMessage(content=content, tool_call_id=tool_id, name=tool_name))
    return tool_messages


async def create_agent_node(
    agent_id: UUID,
    session: AsyncSession,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an agent node function.

    Args:
        agent_id: ID of the agent to use.
        session: Database session.

    Returns:
        Async function that executes the agent.
    """
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")

    provider_config = ProviderConfig(**agent.llm_config)

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
            pass

    model = _create_model(provider_config, tools, agent.output_schema)
    agent_instructions = agent.instructions
    agent_name = agent.name
    tools_by_name = {t.name: t for t in tools}

    async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with the current state."""
        messages: list = []

        if agent_instructions and agent_instructions.strip():
            messages.append(SystemMessage(content=agent_instructions))

        content = _build_context_message(state)
        messages.append(HumanMessage(content=content))

        response = await _run_tool_loop(model, messages, tools_by_name)
        output = _extract_output(response)
        return _build_state_updates(state, agent_name, output)

    return agent_node


def create_agent_node_sync(
    agent: Agent,
    tools: list | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an agent node function from an already-loaded agent.

    This is a synchronous version for use when the agent is already loaded.

    Args:
        agent: Loaded Agent model.
        tools: Optional list of LangChain tools.

    Returns:
        Async function that executes the agent.
    """
    provider_config = ProviderConfig(**agent.llm_config)
    model = _create_model(provider_config, tools, agent.output_schema)
    agent_instructions = agent.instructions
    agent_name = agent.name
    tools_by_name = {t.name: t for t in (tools or [])}

    async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with the current state."""
        messages: list = []
        if agent_instructions and agent_instructions.strip():
            messages.append(SystemMessage(content=agent_instructions))

        content = _build_context_message(state)
        messages.append(HumanMessage(content=content))

        response = await _run_tool_loop(model, messages, tools_by_name)
        output = _extract_output(response)
        return _build_state_updates(state, agent_name, output)

    return agent_node

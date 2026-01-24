"""Agent execution logic."""

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from agent_orchestrator.agents.tool_registry import ToolRegistry
from agent_orchestrator.core.exceptions import SchemaValidationError, ToolExecutionError
from agent_orchestrator.core.interfaces.provider import Message
from agent_orchestrator.core.schemas.agent import AgentConfig
from agent_orchestrator.providers.factory import ProviderFactory
from agent_orchestrator.sessions.manager import SessionManager


@dataclass
class AgentExecutionResult:
    """Result from agent execution."""

    output: Any
    session_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentExecutor:
    """Executes agents with tool calling and structured output."""

    MAX_TOOL_ITERATIONS = 10

    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager
        self._tool_registry = ToolRegistry()

    async def execute(
        self,
        agent_config: AgentConfig,
        user_input: str,
        session_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        """Execute an agent with the given configuration."""
        session = await self._session_manager.get_or_create(session_id)
        provider = ProviderFactory.get_provider(agent_config.model.provider)

        for tool_def in agent_config.tools:
            self._tool_registry.register_custom_tool(tool_def)

        messages = [Message(role="system", content=agent_config.instructions)]

        history = await self._session_manager.get_messages(session.id)
        for msg in history:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        if context:
            context_text = "\n\n".join(f"[{k}]\n{v}" for k, v in context.items() if isinstance(v, str))
            if context_text:
                messages.append(Message(role="user", content=f"Context:\n{context_text}"))

        messages.append(Message(role="user", content=user_input))

        tool_names = [t.name for t in agent_config.tools]
        tools_format = self._tool_registry.to_provider_format(tool_names) if tool_names else None

        output_schema = None
        if agent_config.output_schema:
            output_schema = agent_config.output_schema.schema_definition

        iteration = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        while iteration < self.MAX_TOOL_ITERATIONS:
            response = await provider.complete(
                messages=messages,
                model=agent_config.model.model_name,
                temperature=agent_config.model.temperature,
                max_tokens=agent_config.model.max_tokens,
                tools=tools_format,
                output_schema=output_schema,
            )

            for key in total_usage:
                total_usage[key] += response.usage.get(key, 0)

            if not response.tool_calls:
                await self._session_manager.add_message(session.id, "user", user_input)
                await self._session_manager.add_message(session.id, "assistant", response.content)

                output = response.content
                if output_schema:
                    try:
                        output = json.loads(response.content)
                    except json.JSONDecodeError:
                        pass

                return AgentExecutionResult(
                    output=output,
                    session_id=session.id,
                    metadata={"usage": total_usage, "iterations": iteration + 1},
                )

            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                try:
                    tool = self._tool_registry.get_tool(tool_name)
                    result = await tool.execute(**tool_args)
                    tool_result = json.dumps(result.result) if result.success else f"Error: {result.error}"
                except Exception as e:
                    tool_result = f"Error: {str(e)}"

                messages.append(
                    Message(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tool_call["id"],
                    )
                )

            iteration += 1

        return AgentExecutionResult(
            output="Max tool iterations reached",
            session_id=session.id,
            metadata={"usage": total_usage, "iterations": iteration},
        )

    async def execute_stream(
        self,
        agent_config: AgentConfig,
        user_input: str,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Execute agent with streaming response."""
        session = await self._session_manager.get_or_create(session_id)
        provider = ProviderFactory.get_provider(agent_config.model.provider)

        messages = [Message(role="system", content=agent_config.instructions)]

        history = await self._session_manager.get_messages(session.id)
        for msg in history:
            messages.append(Message(role=msg["role"], content=msg["content"]))

        messages.append(Message(role="user", content=user_input))

        full_response = ""
        async for chunk in provider.stream_complete(
            messages=messages,
            model=agent_config.model.model_name,
            temperature=agent_config.model.temperature,
            max_tokens=agent_config.model.max_tokens,
        ):
            full_response += chunk
            yield chunk

        await self._session_manager.add_message(session.id, "user", user_input)
        await self._session_manager.add_message(session.id, "assistant", full_response)

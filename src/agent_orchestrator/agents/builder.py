"""Agent builder for creating agents from configuration."""

from typing import Any, Callable

from agent_orchestrator.core.interfaces.provider import BaseProvider, Message
from agent_orchestrator.core.interfaces.tool import BaseTool
from agent_orchestrator.core.schemas.agent import AgentConfig


class AgentBuilder:
    """Builds agents from configuration."""

    def build(
        self,
        config: AgentConfig,
        provider: BaseProvider,
        tools: list[BaseTool],
    ) -> Callable[..., Any]:
        """Build an agent callable from configuration."""
        system_message = Message(role="system", content=config.instructions)
        tools_format = self._format_tools(tools)

        async def agent_callable(
            user_input: str,
            history: list[Message] | None = None,
            context: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            messages = [system_message]

            if history:
                messages.extend(history)

            if context and config.file_context:
                context_text = self._build_context_text(context)
                if context_text:
                    messages.append(Message(role="user", content=f"Context:\n{context_text}"))

            messages.append(Message(role="user", content=user_input))

            output_schema = None
            if config.output_schema:
                output_schema = config.output_schema.schema_definition

            response = await provider.complete(
                messages=messages,
                model=config.model.model_name,
                temperature=config.model.temperature,
                max_tokens=config.model.max_tokens,
                tools=tools_format if tools_format else None,
                output_schema=output_schema,
            )

            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
            }

        return agent_callable

    def _format_tools(self, tools: list[BaseTool]) -> list[dict[str, Any]]:
        """Format tools for provider."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema,
            }
            for tool in tools
        ]

    def _build_context_text(self, context: dict[str, Any]) -> str:
        """Build context text from context dictionary."""
        parts = []
        for key, value in context.items():
            if isinstance(value, str):
                parts.append(f"[{key}]\n{value}")
        return "\n\n".join(parts)

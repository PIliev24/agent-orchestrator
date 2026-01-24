"""Anthropic provider implementation."""

import json
from typing import Any, AsyncIterator, Optional

from anthropic import AsyncAnthropic

from agent_orchestrator.core.interfaces.provider import (
    BaseProvider,
    CompletionResponse,
    Message,
)


class AnthropicProvider(BaseProvider):
    """Anthropic API provider implementation."""

    SUPPORTED_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, api_key: str):
        self._client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> list[str]:
        return self.SUPPORTED_MODELS

    async def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        output_schema: Optional[dict[str, Any]] = None,
    ) -> CompletionResponse:
        """Generate completion via Anthropic API."""
        system_content = None
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                api_messages.append(self._convert_message(msg))

        request_params: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens or 4096,
        }

        if system_content:
            request_params["system"] = system_content

        if temperature != 1.0:
            request_params["temperature"] = temperature

        if tools:
            request_params["tools"] = self._format_tools(tools)

        response = await self._client.messages.create(**request_params)

        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    }
                )

        return CompletionResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response.stop_reason or "stop",
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        )

    async def stream_complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        system_content = None
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                api_messages.append(self._convert_message(msg))

        request_params: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens or 4096,
        }

        if system_content:
            request_params["system"] = system_content

        if temperature != 1.0:
            request_params["temperature"] = temperature

        async with self._client.messages.stream(**request_params) as stream:
            async for text in stream.text_stream:
                yield text

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        """Convert internal message to Anthropic format."""
        if msg.role == "tool":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                ],
            }
        return {"role": msg.role, "content": msg.content}

    def _format_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format tools for Anthropic API."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            }
            for tool in tools
        ]

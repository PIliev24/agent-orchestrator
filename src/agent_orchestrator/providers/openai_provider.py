"""OpenAI provider implementation."""

import json
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI

from agent_orchestrator.core.interfaces.provider import (
    BaseProvider,
    CompletionResponse,
    Message,
)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider implementation."""

    SUPPORTED_MODELS = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
    ]

    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

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
        """Generate completion via OpenAI API."""
        request_params: dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages],
            "temperature": temperature,
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if tools:
            request_params["tools"] = self._format_tools(tools)

        if output_schema:
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": output_schema,
                    "strict": True,
                },
            }

        response = await self._client.chat.completions.create(**request_params)

        choice = response.choices[0]
        return CompletionResponse(
            content=choice.message.content or "",
            tool_calls=self._extract_tool_calls(choice.message),
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
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
        request_params: dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if tools:
            request_params["tools"] = self._format_tools(tools)

        stream = await self._client.chat.completions.create(**request_params)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        """Convert internal message to OpenAI format."""
        result: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.tool_calls:
            result["tool_calls"] = msg.tool_calls
        if msg.tool_call_id:
            result["tool_call_id"] = msg.tool_call_id
        return result

    def _format_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format tools for OpenAI API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]

    def _extract_tool_calls(self, message: Any) -> Optional[list[dict[str, Any]]]:
        """Extract tool calls from response message."""
        if not message.tool_calls:
            return None
        return [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ]

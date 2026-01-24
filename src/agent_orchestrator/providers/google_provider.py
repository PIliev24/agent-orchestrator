"""Google Generative AI provider implementation."""

from typing import Any, AsyncIterator, Optional

import google.generativeai as genai

from agent_orchestrator.core.interfaces.provider import (
    BaseProvider,
    CompletionResponse,
    Message,
)


class GoogleProvider(BaseProvider):
    """Google Generative AI provider implementation."""

    SUPPORTED_MODELS = [
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
    ]

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "google"

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
        """Generate completion via Google Generative AI API."""
        generation_config: dict[str, Any] = {"temperature": temperature}

        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens

        if output_schema:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = output_schema

        system_instruction = self._extract_system(messages)

        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

        history = self._convert_history(messages)
        user_message = self._get_last_user_message(messages)

        chat = model_instance.start_chat(history=history)
        response = await chat.send_message_async(user_message)

        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
            }

        return CompletionResponse(
            content=response.text,
            tool_calls=None,
            finish_reason="stop",
            usage=usage,
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
        generation_config: dict[str, Any] = {"temperature": temperature}

        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens

        system_instruction = self._extract_system(messages)

        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

        history = self._convert_history(messages)
        user_message = self._get_last_user_message(messages)

        chat = model_instance.start_chat(history=history)
        response = await chat.send_message_async(user_message, stream=True)

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    def _extract_system(self, messages: list[Message]) -> Optional[str]:
        """Extract system message content."""
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None

    def _convert_history(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert messages to Gemini history format (excluding last user message)."""
        history = []
        for msg in messages[:-1]:
            if msg.role == "system":
                continue
            role = "user" if msg.role == "user" else "model"
            history.append({"role": role, "parts": [msg.content]})
        return history

    def _get_last_user_message(self, messages: list[Message]) -> str:
        """Get the last user message."""
        for msg in reversed(messages):
            if msg.role == "user":
                return msg.content
        return ""

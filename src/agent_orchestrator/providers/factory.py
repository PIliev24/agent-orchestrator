"""Provider factory for creating AI provider instances."""

from typing import Optional

from agent_orchestrator.config import settings
from agent_orchestrator.core.exceptions import ProviderNotConfiguredError
from agent_orchestrator.core.interfaces.provider import BaseProvider
from agent_orchestrator.core.schemas.agent import ModelProvider


class ProviderFactory:
    """Factory for creating AI provider instances."""

    _instances: dict[ModelProvider, BaseProvider] = {}

    @classmethod
    def get_provider(cls, provider: ModelProvider) -> BaseProvider:
        """Get or create a provider instance."""
        if provider not in cls._instances:
            cls._instances[provider] = cls._create_provider(provider)
        return cls._instances[provider]

    @classmethod
    def _create_provider(cls, provider: ModelProvider) -> BaseProvider:
        """Create a new provider instance."""
        from agent_orchestrator.providers.anthropic_provider import AnthropicProvider
        from agent_orchestrator.providers.google_provider import GoogleProvider
        from agent_orchestrator.providers.openai_provider import OpenAIProvider

        match provider:
            case ModelProvider.OPENAI:
                if not settings.openai_api_key:
                    raise ProviderNotConfiguredError("openai")
                return OpenAIProvider(api_key=settings.openai_api_key)
            case ModelProvider.ANTHROPIC:
                if not settings.anthropic_api_key:
                    raise ProviderNotConfiguredError("anthropic")
                return AnthropicProvider(api_key=settings.anthropic_api_key)
            case ModelProvider.GOOGLE:
                if not settings.google_api_key:
                    raise ProviderNotConfiguredError("google")
                return GoogleProvider(api_key=settings.google_api_key)
            case _:
                raise ValueError(f"Unknown provider: {provider}")

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the provider cache."""
        cls._instances.clear()

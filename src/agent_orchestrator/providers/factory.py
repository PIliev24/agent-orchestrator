"""Factory for creating AI providers."""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from agent_orchestrator.core.exceptions import ProviderError
from agent_orchestrator.providers.base import BaseProvider, ProviderConfig
from agent_orchestrator.providers.anthropic import AnthropicProvider
from agent_orchestrator.providers.google import GoogleProvider
from agent_orchestrator.providers.openai import OpenAIProvider


class ProviderFactory:
    """Factory for creating and managing AI providers."""

    _providers: dict[str, type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseProvider]) -> None:
        """Register a new provider.

        Args:
            name: Provider name.
            provider_class: Provider class to register.
        """
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, provider_name: str) -> BaseProvider:
        """Get a provider instance by name.

        Args:
            provider_name: Name of the provider.

        Returns:
            Provider instance.

        Raises:
            ProviderError: If provider is not found.
        """
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ProviderError(
                provider=provider_name,
                message=f"Unknown provider '{provider_name}'. Available: {available}",
            )
        return provider_class()

    @classmethod
    def create_model(
        cls,
        config: ProviderConfig | dict,
        tools: Optional[list[BaseTool]] = None,
        output_schema: Optional[dict] = None,
    ) -> BaseChatModel:
        """Create a chat model from configuration.

        Args:
            config: Provider configuration (ProviderConfig or dict).
            tools: Optional list of tools to bind.
            output_schema: Optional JSON Schema for structured output.

        Returns:
            Configured chat model.

        Raises:
            ProviderError: If model creation fails.
        """
        if isinstance(config, dict):
            config = ProviderConfig(**config)

        try:
            provider = cls.get_provider(config.provider)

            if output_schema:
                return provider.create_model_with_structured_output(config, output_schema)
            elif tools:
                return provider.create_model_with_tools(config, tools)
            else:
                return provider.create_model(config)
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(
                provider=config.provider,
                message=f"Failed to create model: {e}",
                original_error=e,
            )

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available provider names.

        Returns:
            List of provider names.
        """
        return list(cls._providers.keys())

"""Google provider implementation."""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from agent_orchestrator.config import settings
from agent_orchestrator.providers.base import BaseProvider, ProviderConfig


class GoogleProvider(BaseProvider):
    """Provider for Google models (Gemini)."""

    provider_name = "google"

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create a Google chat model.

        Args:
            config: Provider configuration.

        Returns:
            Configured ChatGoogleGenerativeAI instance.
        """
        api_key = config.api_key or settings.google_api_key
        if not api_key:
            raise ValueError("Google API key not configured")

        kwargs = {
            "model": config.model_name,
            "temperature": self.TEMPERATURE,  # Always 0 for deterministic outputs
            "google_api_key": api_key,
            **config.extra_kwargs,
        }

        if config.max_tokens:
            kwargs["max_output_tokens"] = config.max_tokens

        return ChatGoogleGenerativeAI(**kwargs)
